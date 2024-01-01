from __future__ import annotations

import operator
from typing import Iterator, Protocol, Sequence, TypedDict, Union

from gaphor.core.styling.compiler import compile_style_sheet
from gaphor.core.styling.declarations import (
    FONT_SIZE_VALUES,
    Color,
    FontStyle,
    FontWeight,
    JustifyContent,
    Number,
    Padding,
    TextAlign,
    TextDecoration,
    Var,
    VerticalAlign,
    declarations,
    number,
    WhiteSpace,
)

# Style is using SVG properties where possible
# https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute
# NB1. The Style can also contain variables (start with `--`),
#      however those are not part of the interface.
# NB2. The Style can also contain private (`-gaphor-*`) entries.

_Style_after = TypedDict(
    "_Style_after",
    {
        "content": str,
    },
    total=False,
)

Style = TypedDict(
    "Style",
    {
        "background-color": Color,
        "border-radius": Number,
        "color": Color,
        "content": str,
        "dash-style": Sequence[Number],
        "padding": Padding,
        "font-family": str,
        "font-size": Union[int, float, str],
        "font-style": FontStyle,
        "font-weight": FontWeight,
        "justify-content": JustifyContent,
        "line-style": Number,
        "line-width": Number,
        "min-width": Number,
        "min-height": Number,
        "opacity": Number,
        "text-decoration": TextDecoration,
        "text-align": TextAlign,
        "text-color": Color,
        "vertical-align": VerticalAlign,
        "vertical-spacing": Number,
        "white-space": WhiteSpace,
        "::after": _Style_after,
        # Opaque elements to support inheritance
        "-gaphor-style-node": object,
        "-gaphor-compiled-style-sheet": object
    },
    total=False,
)


class StyleNode(Protocol):

    pseudo: str | None
    dark_mode: bool | None

    def name(self) -> str:
        ...

    def parent(self) -> StyleNode | None:
        ...

    def children(self) -> Iterator[StyleNode]:
        ...

    def attribute(self, name: str) -> str:
        ...

    def state(self) -> Sequence[str]:
        ...


class PseudoStyleNode:

    def __init__(self, node: StyleNode, psuedo: str):
        self._node = node
        self.pseudo = psuedo
        self.dark_mode = node.dark_mode

    def name(self) -> str:
        return self._node.name()

    def parent(self) -> StyleNode | None:
        return self._node.parent()

    def children(self) -> Iterator[StyleNode]:
        return self._node.children()

    def attribute(self, name: str) -> str:
        return self._node.attribute(name)

    def state(self) -> Sequence[str]:
        return self._node.state()


def merge_styles(*styles: Style) -> Style:
    style = Style()
    abs_font_size = None
    for s in styles:
        font_size = s.get("font-size")
        if font_size and isinstance(font_size, number):
            abs_font_size = font_size
        style.update(s)

    resolved_style = resolve_variables(style, styles)

    if abs_font_size and resolved_style["font-size"] in FONT_SIZE_VALUES:
        resolved_style["font-size"] = abs_font_size * FONT_SIZE_VALUES[resolved_style["font-size"]]  # type: ignore[index,operator]

    if "opacity" in resolved_style:
        opacity = resolved_style["opacity"]
        for color_prop in ("color", "background-color", "text-color"):
            color: Color | None = resolved_style.get(color_prop)  # type: ignore[assignment]
            if color and color[3] > 0.0:
                resolved_style[color_prop] = color[:3] + (color[3] * opacity,)  # type: ignore[literal-required]

    return resolved_style


def resolve_variables(style: Style, style_layers: Sequence[Style]) -> Style:
    new_style = Style()
    for p, v in style.items():
        if isinstance(v, Var):
            # Go through the individual layers.
            # Fall back if a variable does not resolve.
            for layer in reversed(style_layers):
                if p in layer and (lv := layer[p]):  # type: ignore[literal-required]
                    if isinstance(lv, Var):
                        if (
                            lv.name in style
                            and (
                                resolved := declarations(p, style[lv.name])  # type: ignore[literal-required]
                            )
                            and not isinstance(resolved, Var)
                        ):
                            new_style[p] = resolved  # type: ignore[literal-required]
                            break
                    else:
                        new_style[p] = lv  # type: ignore[literal-required]
                        break
        else:
            new_style[p] = v  # type: ignore[literal-required]
    return new_style


class CompiledStyleSheet:
    def __init__(self, *css: str):
        self.selectors = sorted(
            (
                (selspec[1], order, declarations, selspec[0])
                for order, (selspec, declarations) in enumerate(compile_style_sheet(*css))
                if selspec != "error"
            ),
            key=operator.itemgetter(0, 1),
        )

    def match(self, node: StyleNode) -> Style:
        # TODO: make after_style lazy
        after_style = merge_styles(*(
            declarations
            for _specificity, _order, declarations, pred in self.selectors
            if pred(PseudoStyleNode(node, "after"))
        ))

        return merge_styles(
            {"::after": after_style} if after_style else {},
            {"-gaphor-style-node": node, "-gaphor-compiled-style-sheet": self},
            *(
                declarations
                for _specificity, _order, declarations, pred in self.selectors
                if pred(node)
            )
        )


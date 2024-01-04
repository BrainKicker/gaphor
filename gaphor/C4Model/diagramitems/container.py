from gaphor.C4Model import c4model
from gaphor.core.styling import JustifyContent
from gaphor.diagram.presentation import ElementPresentation, Named, text_name
from gaphor.diagram.shapes import Box, CssNode, Text, draw_border
from gaphor.diagram.support import represents


@represents(c4model.C4Container)
class C4ContainerItem(Named, ElementPresentation):
    def __init__(self, diagram, id=None):
        super().__init__(diagram, id)

        self.watch("subject[NamedElement].name")
        self.watch("subject[C4Container].technology")
        self.watch("subject[C4Container].description")
        self.watch("subject[C4Container].type")
        self.watch("children", self.update_shapes)

    def update_shapes(self, event=None):
        diagram = self.diagram
        self.shape = Box(
            text_name(self),
            CssNode(
                "technology",
                self.subject,
                Text(
                    text=lambda: self.subject.technology
                    and f"[{diagram.gettext(self.subject.type)}: {self.subject.technology}]"
                    or f"[{diagram.gettext(self.subject.type)}]",
                ),
            ),
            *(
                ()
                if self.children
                else (
                    CssNode(
                        "description",
                        self.subject,
                        Text(
                            text=lambda: self.subject.description or "",
                        ),
                    ),
                )
            ),
            style={
                "padding": (4, 4, 4, 4),
                "justify-content": JustifyContent.END
                if self.diagram and self.children
                else JustifyContent.CENTER,
            },
            draw=draw_border,
        )

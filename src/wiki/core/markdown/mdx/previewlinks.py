import markdown
from markdown.treeprocessors import Treeprocessor


class PreviewLinksExtension(markdown.Extension):

    """Markdown Extension that sets all anchor targets to _blank when in preview mode"""

    def extendMarkdown(self, md):

        md.treeprocessors._sort()
        priority = md.treeprocessors._priority[-1].priority - 5
        md.treeprocessors.register(PreviewLinksTree(md), "previewlinks", priority)


class PreviewLinksTree(Treeprocessor):
    def run(self, root):
        if self.md.preview:
            for a in root.findall(".//a"):
                # Do not set target for links like href='#markdown'
                if not a.get("href").startswith("#"):
                    a.set("target", "_blank")
        return root


def makeExtension(*args, **kwargs):
    """Return an instance of the extension."""
    return PreviewLinksExtension(*args, **kwargs)

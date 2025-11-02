"""Content type value object."""

from enum import Enum


class ContentType(str, Enum):
    """Represents the type of content to be generated."""
    
    IMAGE = "image"
    VIDEO = "video"
    TEXT = "text"
    
    def get_default_model(self) -> str:
        """Get the default AI model for this content type."""
        defaults = {
            ContentType.IMAGE: "hunyuan-image-3.0",
            ContentType.VIDEO: "moneyprinter-turbo",
            ContentType.TEXT: "gpt-text-generator",
        }
        return defaults[self]
    
    def get_file_extension(self) -> str:
        """Get the default file extension for this content type."""
        extensions = {
            ContentType.IMAGE: "png",
            ContentType.VIDEO: "mp4",
            ContentType.TEXT: "txt",
        }
        return extensions[self]
    
    def get_mime_type(self) -> str:
        """Get the MIME type for this content type."""
        mime_types = {
            ContentType.IMAGE: "image/png",
            ContentType.VIDEO: "video/mp4",
            ContentType.TEXT: "text/plain",
        }
        return mime_types[self]


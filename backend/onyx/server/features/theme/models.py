from typing import Literal

from pydantic import BaseModel, Field

LogoDisplayStyle = Literal["logo_and_name", "logo_only", "name_only"]


class NavigationItem(BaseModel):
    link: str = Field(max_length=2048)
    icon: str | None = None
    svg_logo: str | None = None
    title: str = Field(max_length=100)


class ThemeSettings(BaseModel):
    """Workspace appearance. Field names match the web `EnterpriseSettings` type."""

    application_name: str | None = Field(default=None, max_length=50)
    use_custom_logo: bool = False
    use_custom_logotype: bool = False
    logo_display_style: LogoDisplayStyle | None = None

    custom_nav_items: list[NavigationItem] = Field(default_factory=list, max_length=20)

    custom_lower_disclaimer_content: str | None = Field(default=None, max_length=500)
    custom_header_content: str | None = Field(default=None, max_length=100)
    two_lines_for_chat_header: bool | None = None
    custom_popup_header: str | None = Field(default=None, max_length=100)
    custom_popup_content: str | None = Field(default=None, max_length=500)
    enable_consent_screen: bool | None = None
    consent_screen_prompt: str | None = Field(default=None, max_length=200)
    show_first_visit_notice: bool | None = None
    custom_greeting_message: str | None = Field(default=None, max_length=50)
    custom_login_subtitle: str | None = Field(default=None, max_length=100)

    custom_help_link_url: str | None = Field(default=None, max_length=2048)
    custom_help_link_label: str | None = Field(default=None, max_length=100)

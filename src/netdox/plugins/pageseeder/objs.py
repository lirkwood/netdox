# from __future__ import annotations
# from lxml import etree
# from dataclasses import dataclass

# @dataclass
# class License:
#     domain: str
#     """Domain name this license is bound to."""
#     org_uriid: str
#     """Associated organization document URIID as a string."""

#     @classmethod
#     def from_psml(cls, psml: str) -> License:
#         tree: etree._Element = etree.fromstring(psml)
#         details = tree.find("document/section[@id = 'details']/properties-fragment")
#         return cls(
#             tree.find("document/section[@id = 'title']/fragment/heading").text,
#             details.find("property[@name = 'organization']/xref/@uriid").text
#         )

from typing import *
import warnings, logging
import xml.etree.ElementTree as ET
import requests, bz2, os, gzip, re, ujson
from tqdm.auto import tqdm
from dataclasses import dataclass, asdict, field
from pathlib import Path
from operator import itemgetter
from itertools import islice
import deprecation
from urllib.parse import urlparse, unquote_plus


"""Module containing code for parsing wikipedia dump from DBPedia at 2016. This module is deprecated as we do not parse the data directly any more
"""

logger = logging.getLogger("wikipedia")


@dataclass
class WikiPageArticle:
    # Original schema: https://www.mediawiki.org/xml/export-0.10.xsd
    # properties of PageType
    # page.id
    id: int
    # page.ns
    ns: str
    # page.title
    title: str
    # page.redirect.title (since RedirectType only has title property), flag this current revision is a redirect
    redirect_title: Optional[str]

    # properties of revision
    # page.revision.model
    model: str
    # page.revision.format
    format: str
    # page.revision.text
    text: str

    @property
    def url(self):
        return f"https://en.wikipedia.org/wiki/{self.title.replace(' ', '_')}?curid={self.id}"


@dataclass
class WikiPageExtractedTables:
    id: int
    ns: str
    title: str
    text: str
    raw_tables: List[str]

    @property
    def url(self):
        return f"https://en.wikipedia.org/wiki/{self.title.replace(' ', '_')}?curid={self.id}"


@dataclass
class Cell:
    value: Union[str, 'Table']
    attrs: Dict[str, str] = field(default_factory=dict)
    is_header: bool = False

    def is_literal(self):
        return isinstance(self.value, (str,))


@dataclass
class Row:
    cells: List[Cell]
    attrs: Dict[str, str] = field(default_factory=dict)


@dataclass
class Table:
    rows: List[Row]
    caption: Optional[str] = None
    attrs: Dict[str, str] = field(default_factory=dict)

    @staticmethod
    def parse(text: str):
        return TableVisitor().parse(text)


def get_title_from_url(url: str) -> str:
    """This function converts a wikipedia page/article's URL to its title. The function is tested manually in `20200425-wikipedia-links` notebook in section 2.2.

    Parameters
    ----------
    url : str
        a wikipedia page/article's URL

    Returns
    -------
    str
        a wikipedia page/article's title
    """
    path = urlparse(url).path
    assert path.startswith("/wiki/"), path
    path = path[6:]
    title = unquote_plus(path).replace("_", " ")
    return title.strip()



# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Front Matter.
#
# Rogue Scholar is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Redirector functions and rules for legacy URLs."""

import re
from flask import request, url_for


def camelcase_to_titlecase(s):
    t = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)
    return t[0].upper() + t[1:].lower()


def blogs_detail_view_function():
    """Implements redirector view function for blogs detail.

    The following routes are redirected as follows:
        - /blogs/<id>/ -> GET /communities/<pid_value>

    :return: url for the view 'invenio_app_rdm_communities.communities_detail'
    :rtype: str
    """
    _id = request.view_args["id"]
    values = {"pid_value": _id}
    target = url_for(
        "invenio_app_rdm_communities.communities_detail", **values
    )
    return target


def blogs_search_view_function():
    """Implements redirector view function for blogs search.

    The following routes are redirected as follows:
        - /blogs -> GET /communities/search?q=<query>&f=<tags>&p=<page>

    :return: url for the view 'invenio_communities.communities_search'
    :rtype: str
    """
    _q = request.args.get("query", "")
    category = request.args.get("category", None)
    _f = ""
    if category:
        category = camelcase_to_titlecase(category)
        _f = f"subject:{category}"
    _p = request.args.get("page", 1)
    values = {"q": _q, "f": _f, "p": _p}
    target = url_for("invenio_communities.communities_search", **values)
    return target


def posts_detail_view_function():
    """Implements redirector view function for posts detail.
    Assumes that the pid_value is a DOI.

    The following routes are redirected as follows:
        - /posts/<prefix>/<suffix> -> GET /search?q=doi:<pid_value>

    :return: url for the view 'invenio_search_ui.search'
    :rtype: str
    """
    prefix = request.view_args["prefix"]
    suffix = request.view_args["suffix"]
    values = {"q": f"doi:{prefix}/{suffix}"}
    target = url_for("invenio_search_ui.search", **values)
    return target


def posts_search_view_function():
    """Implements redirector view function for posts search.

    The following routes are redirected as follows:
        - /posts -> GET /search?q=<query>&f=<tags>&p=<page>

    :return: url for the view 'invenio_search_ui.search'
    :rtype: str
    """
    _q = request.args.get("query", "")
    category = request.args.get("category", None)
    tags = request.args.get("tags", None)
    _f = ""
    if category:
        category = camelcase_to_titlecase(category)
        _f = f"subject:{category}"
    if tags:
        _f = f"subject:{tags}"
    _p = request.args.get("page", 1)
    values = {"q": _q, "f": _f, "p": _p}
    target = url_for("invenio_search_ui.search", **values)
    return target


REDIRECTOR_RULES = {
    "redirect_blogs": {
        "source": "/blogs",
        "target": blogs_search_view_function,
    },
    "redirect_en_blogs": {
        "source": "/en/blogs",
        "target": blogs_search_view_function,
    },
    "redirect_de_blogs": {
        "source": "/de/blogs",
        "target": blogs_search_view_function,
    },
    "redirect_es_blogs": {
        "source": "/es/blogs",
        "target": blogs_search_view_function,
    },
    "redirect_fr_blogs": {
        "source": "/fr/blogs",
        "target": blogs_search_view_function,
    },
    "redirect_pt_blogs": {
        "source": "/pt/blogs",
        "target": blogs_search_view_function,
    },
    "redirect_it_blogs": {
        "source": "/it/blogs",
        "target": blogs_search_view_function,
    },
    "redirect_tr_blogs": {
        "source": "/tr/blogs",
        "target": blogs_search_view_function,
    },
    "redirect_blogs_detail": {
        "source": "/blogs/<id>",
        "target": blogs_detail_view_function,
    },
    "redirect_en_blogs_detail": {
        "source": "/en/blogs/<id>",
        "target": blogs_detail_view_function,
    },
    "redirect_de_blogs_detail": {
        "source": "/de/blogs/<id>",
        "target": blogs_detail_view_function,
    },
    "redirect_es_blogs_detail": {
        "source": "/es/blogs/<id>",
        "target": blogs_detail_view_function,
    },
    "redirect_fr_blogs_detail": {
        "source": "/fr/blogs/<id>",
        "target": blogs_detail_view_function,
    },
    "redirect_pt_blogs_detail": {
        "source": "/pt/blogs/<id>",
        "target": blogs_detail_view_function,
    },
    "redirect_it_blogs_detail": {
        "source": "/it/blogs/<id>",
        "target": blogs_detail_view_function,
    },
    "redirect_tr_blogs_detail": {
        "source": "/tr/blogs/<id>",
        "target": blogs_detail_view_function,
    },
    "redirect_posts": {
        "source": "/posts",
        "target": posts_search_view_function,
    },
    "redirect_en": {
        "source": "/en",
        "target": posts_search_view_function,
    },
    "redirect_de": {
        "source": "/de",
        "target": posts_search_view_function,
    },
    "redirect_es": {
        "source": "/es",
        "target": posts_search_view_function,
    },
    "redirect_fr": {
        "source": "/fr",
        "target": posts_search_view_function,
    },
    "redirect_pt": {
        "source": "/pt",
        "target": posts_search_view_function,
    },
    "redirect_it": {
        "source": "/it",
        "target": posts_search_view_function,
    },
    "redirect_tr": {
        "source": "/tr",
        "target": posts_search_view_function,
    },
    "redirect_en_posts": {
        "source": "/en/posts",
        "target": posts_search_view_function,
    },
    "redirect_de_posts": {
        "source": "/de/posts",
        "target": posts_search_view_function,
    },
    "redirect_es_posts": {
        "source": "/es/posts",
        "target": posts_search_view_function,
    },
    "redirect_fr_posts": {
        "source": "/fr/posts",
        "target": posts_search_view_function,
    },
    "redirect_pt_posts": {
        "source": "/pt/posts",
        "target": posts_search_view_function,
    },
    "redirect_it_posts": {
        "source": "/it/posts",
        "target": posts_search_view_function,
    },
    "redirect_tr_posts": {
        "source": "/tr/posts",
        "target": posts_search_view_function,
    },
    "redirect_posts_search": {
        "source": "/posts/<prefix>/<suffix>",
        "target": posts_detail_view_function,
    },
    "redirect_en_posts_search": {
        "source": "/en/posts/<prefix>/<suffix>",
        "target": posts_detail_view_function,
    },
    "redirect_de_posts_search": {
        "source": "/de/posts/<prefix>/<suffix>",
        "target": posts_detail_view_function,
    },
    "redirect_es_posts_search": {
        "source": "/es/posts/<prefix>/<suffix>",
        "target": posts_detail_view_function,
    },
    "redirect_fr_posts_search": {
        "source": "/fr/posts/<prefix>/<suffix>",
        "target": posts_detail_view_function,
    },
    "redirect_pt_posts_search": {
        "source": "/pt/posts/<prefix>/<suffix>",
        "target": posts_detail_view_function,
    },
    "redirect_it_posts_search": {
        "source": "/it/posts/<prefix>/<suffix>",
        "target": posts_detail_view_function,
    },
    "redirect_tr_posts_search": {
        "source": "/tr/posts/<prefix>/<suffix>",
        "target": posts_detail_view_function,
    },
}

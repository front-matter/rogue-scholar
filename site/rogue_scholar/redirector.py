# -*- coding: utf-8 -*-
#
# Copyright (C) 2025-2026 Front Matter.
#
# Rogue Scholar is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Redirector functions and rules for legacy URLs."""

import re
from flask import request, url_for


# Redirection of legacy URLs
# --------------------------


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
    _id = (request.view_args or {}).get("id", "")
    target = url_for(
        "invenio_app_rdm_communities.communities_detail",
        pid_value=str(_id),
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
    category = request.args.get("category")
    _f = ""
    if category:
        category = camelcase_to_titlecase(category)
        _f = f"subject:{category}"
    _p = request.args.get("page", "1")
    target = url_for(
        "invenio_communities.communities_search",
        q=_q,
        f=_f,
        p=_p,
    )
    return target


def posts_detail_view_function():
    """Implements redirector view function for posts detail.
    Assumes that the pid_value is a DOI.

    The following routes are redirected as follows:
        - /posts/<prefix>/<suffix> -> GET /search?q=doi:<pid_value>

    :return: url for the view 'invenio_search_ui.search'
    :rtype: str
    """
    prefix = (request.view_args or {}).get("prefix", "")
    suffix = (request.view_args or {}).get("suffix", "")
    target = url_for("invenio_search_ui.search", q=f"doi:{prefix}/{suffix}")
    return target


def posts_search_view_function():
    """Implements redirector view function for posts search.

    The following routes are redirected as follows:
        - /posts -> GET /search?q=<query>&f=<tags>&p=<page>

    :return: url for the view 'invenio_search_ui.search'
    :rtype: str
    """
    _q = request.args.get("query", "")
    category = request.args.get("category")
    tags = request.args.get("tags")
    _f = ""
    if category:
        category = camelcase_to_titlecase(category)
        _f = f"subject:{category}"
    if tags:
        _f = f"subject:{tags}"
    _p = request.args.get("page", "1")
    target = url_for("invenio_search_ui.search", q=_q, f=_f, p=_p)
    return target


LOCALES = ("en", "de", "es", "fr", "pt", "it", "tr")


def _add_rule(rules, name, source, target):
    rules[name] = {"source": source, "target": target}


def _build_redirector_rules():
    rules = {}

    _add_rule(rules, "redirect_blogs", "/blogs", blogs_search_view_function)
    _add_rule(
        rules,
        "redirect_blogs_detail",
        "/blogs/<id>",
        blogs_detail_view_function,
    )
    _add_rule(rules, "redirect_posts", "/posts", posts_search_view_function)
    _add_rule(
        rules,
        "redirect_posts_search",
        "/posts/<prefix>/<suffix>",
        posts_detail_view_function,
    )

    for locale in LOCALES:
        _add_rule(
            rules,
            f"redirect_{locale}_blogs",
            f"/{locale}/blogs",
            blogs_search_view_function,
        )
        _add_rule(
            rules,
            f"redirect_{locale}_blogs_detail",
            f"/{locale}/blogs/<id>",
            blogs_detail_view_function,
        )
        _add_rule(
            rules,
            f"redirect_{locale}",
            f"/{locale}",
            posts_search_view_function,
        )
        _add_rule(
            rules,
            f"redirect_{locale}_posts",
            f"/{locale}/posts",
            posts_search_view_function,
        )
        _add_rule(
            rules,
            f"redirect_{locale}_posts_search",
            f"/{locale}/posts/<prefix>/<suffix>",
            posts_detail_view_function,
        )

    return rules


REDIRECTOR_RULES = _build_redirector_rules()

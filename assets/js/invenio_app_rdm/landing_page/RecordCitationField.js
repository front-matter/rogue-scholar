// This file is part of InvenioRDM
// Copyright (C) 2021-2025 CERN.
// Copyright (C) 2021 Graz University of Technology.
// Copyright (C) 2021 TU Wien
//
// Invenio RDM Records is free software; you can redistribute it and/or modify it
// under the terms of the MIT License; see LICENSE file for more details.

import _debounce from "lodash/debounce";
import React, { Component } from "react";
import PropTypes from "prop-types";
import { Placeholder, Dropdown, Message } from "semantic-ui-react";
import { withCancel } from "react-invenio-forms";
import { CopyButton } from "../components/CopyButton";
import { i18next } from "@translations/invenio_app_rdm/i18next";
import { http } from "react-invenio-forms";

export class RecordCitationField extends Component {
  constructor(props) {
    super(props);

    this.state = {
      loading: true,
      citation: "",
      error: null,
    };
  }

  componentDidMount() {
    const { recordLinks, defaultStyle, includeDeleted } = this.props;
    this.getCitation(recordLinks, defaultStyle, includeDeleted);
  }

  async componentDidUpdate() {
    await window.MathJax?.typesetPromise();
  }

  componentWillUnmount() {
    this.cancellableFetchCitation?.cancel();
  }

  placeholderLoader = () => {
    return (
      <Placeholder>
        <Placeholder.Paragraph>
          <Placeholder.Line />
          <Placeholder.Line />
          <Placeholder.Line />
        </Placeholder.Paragraph>
      </Placeholder>
    );
  };

  errorMessage = (message) => {
    return <Message negative>{message}</Message>;
  };

  fetchCitation = async (recordLinks, style, includeDeleted) => {
    const includeDeletedParam =
      includeDeleted === true ? "&include_deleted=1" : "";
    // Prefer explicit locale prop (server-side), fall back to i18next or browser
    // Use only the base language code (e.g. "de" from "de_DE" or "de-DE")
    // for maximum CSL style compatibility — not all styles have regional locale files
    const rawLocale =
      this.props.locale || i18next.language || navigator.language;
    const locale = rawLocale.split(/[-_]/)[0];
    const url = `${recordLinks.self}?locale=${locale}&style=${style}${includeDeletedParam}`;
    try {
      return await http.get(url, {
        headers: { Accept: "text/x-bibliography" },
      });
    } catch (error) {
      // Some CSL styles lack locale data and crash citeproc-py with a non-English
      // locale (TypeError: 'NoneType' object is not iterable in citeproc/model.py).
      // Fall back to English in that case.
      if (locale !== "en" && error?.response?.status === 500) {
        const fallbackUrl = `${recordLinks.self}?locale=en&style=${style}${includeDeletedParam}`;
        return await http.get(fallbackUrl, {
          headers: { Accept: "text/x-bibliography" },
        });
      }
      throw error;
    }
  };

  getCitation = async (recordLinks, style, includeDeleted) => {
    this.setState({
      loading: true,
      citation: "",
      error: "",
    });

    this.cancellableFetchCitation = withCancel(
      this.fetchCitation(recordLinks, style, includeDeleted),
    );

    try {
      const response = await this.cancellableFetchCitation.promise;
      this.setState({
        loading: false,
        citation: response.data,
      });
    } catch (error) {
      if (error !== "UNMOUNTED") {
        this.setState({
          loading: false,
          citation: "",
          error: i18next.t("An error occurred while generating the citation."),
        });
      }
    }
  };

  render() {
    const { styles, recordLinks, defaultStyle, includeDeleted } = this.props;
    const { loading, citation, error } = this.state;
    const normalizedStyles = Array.isArray(styles)
      ? styles
      : typeof styles === "string"
      ? [[styles, styles]]
      : [];
    const citationOptions = normalizedStyles.map((style) => {
      const value = Array.isArray(style) ? style[0] : style;
      const label = Array.isArray(style) ? style[1] : style;
      return {
        key: value,
        value,
        text: label,
      };
    });

    // convert links in text to clickable links (ignoring punctuations at the end)
    const urlRegex = /(https?:\/\/[^\s,;]+(?=[^\s,;]*))/g;
    const citationText =
      typeof citation === "string" ? citation : String(citation || "");
    const urlizedCitation = citationText.replace(urlRegex, (url) => {
      // remove trailing dot
      let trailingDot = "";
      if (url.endsWith(".")) {
        trailingDot = ".";
        url = url.slice(0, -1);
      }
      return `<a href="${url}" target="_blank">${url}</a>${trailingDot}`;
    });

    return (
      <div>
        <div id="citation-text" className="wrap-overflowing-text rel-mb-2">
          {loading ? (
            this.placeholderLoader()
          ) : (
            <div dangerouslySetInnerHTML={{ __html: urlizedCitation }} />
          )}
        </div>

        <div className="auto-column-grid no-wrap">
          <div className="flex align-items-center">
            <label id="citation-style-label" className="mr-10">
              {i18next.t("Style")}
            </label>
            <Dropdown
              className="citation-dropdown"
              aria-labelledby="citation-style-label"
              defaultValue={defaultStyle}
              options={citationOptions}
              selection
              onChange={_debounce(
                (event, data) =>
                  this.getCitation(recordLinks, data.value, includeDeleted),
                500,
              )}
            />
          </div>
          <CopyButton text={citation} />
        </div>
        {error ? this.errorMessage(error) : null}
      </div>
    );
  }
}

RecordCitationField.propTypes = {
  styles: PropTypes.oneOfType([PropTypes.array, PropTypes.string]),
  recordLinks: PropTypes.object.isRequired,
  defaultStyle: PropTypes.string.isRequired,
  includeDeleted: PropTypes.bool.isRequired,
  locale: PropTypes.string,
};

RecordCitationField.defaultProps = {
  styles: [],
  locale: undefined,
};

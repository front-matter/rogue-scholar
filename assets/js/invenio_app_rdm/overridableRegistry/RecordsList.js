// This file is part of InvenioRDM
// Copyright (C) 2022-2024 CERN.
// Copyright (C) 2025 Front Matter.
//
// Invenio RDM is free software; you can redistribute it and/or modify it
// under the terms of the MIT License; see LICENSE file for more details.

import React, { Component } from "react";
import PropTypes from "prop-types";
import { i18next } from "@translations/invenio_app_rdm/i18next";
import { withCancel, http } from "react-invenio-forms";

// Add custom translations for this component
const customTranslations = {
  en: {
    "No records found.": "No records in English found.",
    "Search all records": "Search all records",
  },
  de: {
    "No records found.": "Keine Beiträge auf Deutsch gefunden.",
    "Search all records": "Alle Beiträge durchsuchen",
  },
  es: {
    "No records found.": "No se encontraron publicaciones en español.",
    "Search all records": "Buscar todas las publicaciones",
  },
  fr: {
    "No records found.": "Aucun article en français trouvé.",
    "Search all records": "Rechercher tous les articles",
  },
};

Object.entries(customTranslations).forEach(([lng, resources]) => {
  i18next.addResourceBundle(lng, "translation", resources, true, false);
});
import {
  Placeholder,
  Divider,
  Container,
  Header,
  Item,
  Button,
  Message,
} from "semantic-ui-react";
import RecordsResultsListItem from "./RecordsResultsListItem";
import isEmpty from "lodash/isEmpty";

class RecordsList extends Component {
  constructor(props) {
    super(props);

    this.state = {
      data: { hits: [] },
      isLoading: false,
      error: null,
    };
  }

  componentDidMount() {
    this.fetchData();
  }

  componentWillUnmount() {
    this.cancellableFetch && this.cancellableFetch.cancel();
  }

  fetchData = async () => {
    const { fetchUrl } = this.props;
    this.setState({ isLoading: true });

    this.cancellableFetch = withCancel(
      http.get(fetchUrl, {
        headers: {
          Accept: "application/vnd.inveniordm.v1+json",
        },
      }),
    );

    try {
      const response = await this.cancellableFetch.promise;
      this.setState({ data: response.data.hits, isLoading: false });
    } catch (error) {
      console.error(error);
      this.setState({ error: error.response.data.message, isLoading: false });
    }
  };

  renderPlaceHolder = () => {
    const { title } = this.props;

    return (
      <Container>
        <Header as="h2">{title}</Header>
        {Array.from(Array(10)).map((item, index) => (
          <div key={index}>
            <Placeholder fluid className="rel-mt-3">
              <Placeholder.Header>
                <Placeholder.Line />
              </Placeholder.Header>

              <Placeholder.Paragraph>
                <Placeholder.Line />
              </Placeholder.Paragraph>

              <Placeholder.Paragraph>
                <Placeholder.Line />
                <Placeholder.Line />
                <Placeholder.Line />
              </Placeholder.Paragraph>
            </Placeholder>

            {index < 9 && <Divider className="rel-mt-2 rel-mb-2" />}
          </div>
        ))}
      </Container>
    );
  };

  render() {
    const { isLoading, data, error } = this.state;
    const { title, appName } = this.props;

    const listItems = data.hits?.map((record) => {
      return (
        <RecordsResultsListItem
          result={record}
          key={record.id}
          appName={appName}
        />
      );
    });

    return (
      <>
        {isLoading && this.renderPlaceHolder()}

        {!isLoading && !error && !isEmpty(listItems) && (
          <Container>
            <Header as="h2">{title}</Header>

            <Item.Group relaxed link divided>
              {listItems}
            </Item.Group>

            <Container textAlign="center">
              <Button href="/search">{i18next.t("More")}</Button>
            </Container>
          </Container>
        )}

        {!isLoading && !error && isEmpty(listItems) && (
          <Container>
            <Header as="h2">{title}</Header>
            <Message info>
              <Message.Content>
                <p>{i18next.t("No records found.")}</p>
                <Button href="/search" primary>
                  {i18next.t("Search all records")}
                </Button>
              </Message.Content>
            </Message>
          </Container>
        )}

        {!isLoading && error && (
          <Container>
            <Header as="h2">{title}</Header>
            <Message content={error} error icon="warning sign" />
          </Container>
        )}
      </>
    );
  }
}

RecordsList.propTypes = {
  title: PropTypes.string.isRequired,
  fetchUrl: PropTypes.string.isRequired,
  appName: PropTypes.string,
};

RecordsList.defaultProps = {
  appName: "",
};

export default RecordsList;

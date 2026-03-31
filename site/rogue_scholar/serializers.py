from marshmallow import Schema, fields

from invenio_vocabularies.resources import L10NString


class SubjectL10NItemSchema(Schema):
    """Localized serializer schema for subjects autocomplete results."""

    id = fields.String(dump_only=True)
    title = L10NString(data_key="title_l10n")
    subject = fields.String(dump_only=True)
    scheme = fields.String(dump_only=True)
    props = fields.Dict(dump_only=True)

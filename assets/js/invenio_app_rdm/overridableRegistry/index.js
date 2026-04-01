// This file is part of InvenioRDM
// Copyright (C) 2026 Front Matter.
//
// Invenio RDM is free software; you can redistribute it and/or modify it
// under the terms of the MIT License; see LICENSE file for more details.

import { overriddenComponents } from "./mapping";
import { overrideStore } from "react-overridable";

for (const [key, value] of Object.entries(overriddenComponents)) {
  overrideStore.add(key, value);
}

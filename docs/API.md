# API Draft

## Endpoints

```http
POST /projects
GET /projects/{project_id}
POST /projects/{project_id}/decisions
GET /decisions/{decision_id}
POST /decisions/{decision_id}/proposals
POST /decisions/{decision_id}/evidence
POST /decisions/{decision_id}/outcomes
POST /decisions/{decision_id}/reflections
GET /projects/{project_id}/graph
```

## Design notes

The API should remain model-agnostic and implementation-neutral.

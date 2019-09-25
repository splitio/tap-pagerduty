# tap-datadog

This is a [Singer](https://singer.io) tap that produces JSON-formatted data
following the [Singer
spec](https://github.com/singer-io/getting-started/blob/master/SPEC.md).

This tap:

- Pulls raw data from [Pagerduty](https://api-reference.pagerduty.com/#!/API_Reference/get_api_reference)
- Extracts the following resources:
  - [Alerts](https://api-reference.pagerduty.com/#!/Incidents/get_incidents_id_alerts)
  - [Escalation Policies](https://api-reference.pagerduty.com/#!/Escalation_Policies/get_escalation_policies)
  - [Incidents](https://api-reference.pagerduty.com/#!/Incidents/get_incidents)
  - [Services](https://api-reference.pagerduty.com/#!/Services/get_services)
  - [Teams](https://api-reference.pagerduty.com/#!/Teams/get_teams)
  - [Users](https://api-reference.pagerduty.com/#!/Users/get_users)
  - [Vendors](https://api-reference.pagerduty.com/#!/Vendors/get_vendors)
- Outputs the schema for each resource
- Incrementally pulls data based on the input state

## Config

*config.json*
```json
{
  "api_token": "THISISATOKEN",
  "start_date": "2000-01-01T00:00:00Z"
}
```

resource "grafana_data_source" "prometheus" {
  type       = "prometheus"
  name       = "prometheus-terraform"
  uid        = "ticketcore-prom-id"
  url        = "http://prometheus:9090"
  is_default = true

  json_data_encoded = jsonencode({
    httpMethod   = "POST"
    timeInterval = "15s"
  })
}

resource "grafana_folder" "core_metrics" {
  title = "TicketCore Production"
}

resource "grafana_dashboard" "dashboard1" {
  folder      = grafana_folder.core_metrics.id
  config_json = file("${path.module}/dashboards/dashboard1.json")
  overwrite   = true
}
{{- define "helm-demo.fullname" -}}
{{ .Release.Name }}
{{- end -}}

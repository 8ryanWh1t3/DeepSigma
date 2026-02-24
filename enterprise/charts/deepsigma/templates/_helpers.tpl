{{- define "deepsigma.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "deepsigma.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "deepsigma.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "deepsigma.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "deepsigma.selectorLabels" -}}
app.kubernetes.io/name: {{ include "deepsigma.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "deepsigma.componentLabels" -}}
{{ include "deepsigma.selectorLabels" . }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{- define "deepsigma.componentName" -}}
{{ include "deepsigma.fullname" . }}-{{ .component }}
{{- end }}

{{- define "deepsigma.configMapName" -}}
{{ include "deepsigma.fullname" . }}-config
{{- end }}

{{- define "deepsigma.secretName" -}}
{{ include "deepsigma.fullname" . }}-secret
{{- end }}

{{- define "deepsigma.dataPvcName" -}}
{{- if .Values.dataPersistence.existingClaim }}
{{ .Values.dataPersistence.existingClaim }}
{{- else }}
{{ include "deepsigma.fullname" . }}-data
{{- end }}
{{- end }}

{{- define "deepsigma.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "deepsigma.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

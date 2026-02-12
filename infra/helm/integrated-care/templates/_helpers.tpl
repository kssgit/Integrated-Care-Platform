{{- define "integrated-care.name" -}}
{{- default .Chart.Name .Values.global.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "integrated-care.fullname" -}}
{{- if .Values.global.fullnameOverride -}}
{{- .Values.global.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "integrated-care.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "integrated-care.labels" -}}
app.kubernetes.io/name: {{ include "integrated-care.name" . }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "integrated-care.databaseUrl" -}}
{{- if .Values.secret.DATABASE_URL -}}
{{- .Values.secret.DATABASE_URL -}}
{{- else if .Values.dependencies.postgresql.enabled -}}
{{- printf "postgresql://%s:%s@%s-postgresql:5432/%s" .Values.postgresql.auth.username .Values.postgresql.auth.password .Release.Name .Values.postgresql.auth.database -}}
{{- else -}}
{{- "" -}}
{{- end -}}
{{- end -}}

{{- define "integrated-care.redisUrl" -}}
{{- if .Values.secret.REDIS_URL -}}
{{- .Values.secret.REDIS_URL -}}
{{- else if .Values.dependencies.redis.enabled -}}
{{- printf "redis://%s-redis-master:6379/0" .Release.Name -}}
{{- else -}}
{{- "" -}}
{{- end -}}
{{- end -}}

{{- define "integrated-care.kafkaBootstrapServers" -}}
{{- if .Values.secret.KAFKA_BOOTSTRAP_SERVERS -}}
{{- .Values.secret.KAFKA_BOOTSTRAP_SERVERS -}}
{{- else if .Values.dependencies.kafka.enabled -}}
{{- printf "%s-kafka:9092" .Release.Name -}}
{{- else -}}
{{- "" -}}
{{- end -}}
{{- end -}}

# ---- Build stage ----
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app
COPY pom.xml .
RUN mvn -B dependency:go-offline
COPY src ./src
RUN mvn -B -DskipTests package

# ---- Runtime stage ----
FROM eclipse-temurin:17-jre

# Install tini for proper PID 1 signal handling in K8s + Python 3 for scripts
RUN apt-get update && apt-get install -y --no-install-recommends tini python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user
RUN groupadd -r autorun && useradd -r -g autorun -m -s /bin/bash autorun \
    && mkdir -p /app/data/scripts /app/data/logs \
    && chown -R autorun:autorun /app/data

# Copy application
COPY --from=build --chown=autorun:autorun /app/target/autorun-*.jar app.jar

USER autorun

EXPOSE 8080

# JVM flags tuned for container environments:
#   -XX:+UseContainerSupport    : respect cgroup memory limits
#   -XX:MaxRAMPercentage=75     : use 75% of container memory limit
#   -XX:+UseG1GC               : low-pause GC for web apps
#   -Djava.security.egd        : faster entropy for JWT
#   -Dfile.encoding=UTF-8      : consistent encoding
#   -Duser.timezone=UTC        : consistent timestamps
ENV JAVA_OPTS="-XX:+UseContainerSupport \
-XX:MaxRAMPercentage=75.0 \
-XX:InitialRAMPercentage=50.0 \
-XX:+UseG1GC \
-XX:MaxGCPauseMillis=200 \
-Djava.security.egd=file:/dev/./urandom \
-Dfile.encoding=UTF-8 \
-Duser.timezone=UTC"

ENV AUTORUN_PYTHON_INTERPRETER=python3

ENTRYPOINT ["tini", "--", "sh", "-c", "java $JAVA_OPTS -jar app.jar"]

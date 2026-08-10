# ---- Build stage ----
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app
COPY pom.xml .
RUN mvn -B dependency:go-offline
COPY src ./src
RUN mvn -B -DskipTests package

# ---- Runtime stage ----
FROM eclipse-temurin:17-jre
WORKDIR /app
RUN useradd -m -s /bin/bash autorun \
    && mkdir -p /app/data/scripts /app/data/logs \
    && chown -R autorun:autorun /app/data
USER autorun
COPY --from=build /app/target/autorun-*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]

# Contributing to AutoRun

Thanks for your interest in contributing! AutoRun is a portfolio project and welcomes community contributions.

## Development Setup

**Prerequisites:** Java 17+ and Maven 3.9+ (or use `./mvnw`).

```bash
git clone https://github.com/ogc16/autorun.git
cd autorun
mvn -DskipTests package
java -jar target/autorun-1.0.0.jar
```

Sign in with `admin` / `admin123`.

## Running Tests

```bash
./mvnw test
```

The test suite covers:
- Application context load and data seeding
- Auth API (login, token refresh, RBAC)
- Full execution pipeline (upload → execute → verify output → timeout)

## Submitting Changes

1. Fork the repository and create a feature branch from `main`.
2. Make your changes. Follow the existing code style.
3. Run the full test suite: `./mvnw clean test`.
4. Ensure CI passes on your branch before opening a PR.
5. Write a clear PR description explaining **what** changed and **why**.

## Code Style

- Java 17 (text blocks, switch expressions, records).
- Lombok for boilerplate (`@Getter`, `@Setter`, `@NoArgsConstructor`).
- Follow existing patterns — controllers are thin, logic lives in services.
- No new dependencies without discussion in an issue first.

## Reporting Bugs

Open an issue with:
- Steps to reproduce
- Expected vs actual behavior
- OS and Java version
- Logs if available

## Security Issues

See [SECURITY.md](SECURITY.md). **Do not** open public issues for security vulnerabilities.

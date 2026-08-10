package com.autorun.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

@Service
public class StorageService {

    private final Path scriptDir;
    private final Path logDir;

    public StorageService(@Value("${autorun.storage-dir}") String storageDir,
                          @Value("${autorun.log-dir}") String logDir) {
        this.scriptDir = Path.of(storageDir).toAbsolutePath().normalize();
        this.logDir = Path.of(logDir).toAbsolutePath().normalize();
        try {
            Files.createDirectories(this.scriptDir);
            Files.createDirectories(this.logDir);
        } catch (IOException e) {
            throw new UncheckedIOException("Unable to create storage directories", e);
        }
    }

    public Path scriptPath(String filename) {
        return scriptDir.resolve(filename).normalize();
    }

    public Path getScriptDir() {
        return scriptDir;
    }

    public Path logPath(String filename) {
        return logDir.resolve(filename).normalize();
    }

    public void writeScript(String filename, byte[] content) {
        Path target = scriptPath(filename);
        if (!target.startsWith(scriptDir)) {
            throw new IllegalArgumentException("Invalid script path");
        }
        try {
            Files.write(target, content, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);
        } catch (IOException e) {
            throw new UncheckedIOException("Failed to store script file", e);
        }
    }

    public void deleteScript(String filename) {
        try {
            Files.deleteIfExists(scriptPath(filename));
        } catch (IOException e) {
            throw new UncheckedIOException("Failed to delete script file", e);
        }
    }

    public String readScriptContent(String filename) {
        try {
            return Files.readString(scriptPath(filename), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException("Failed to read script content", e);
        }
    }

    public byte[] readScriptBytes(String filename) {
        try {
            return Files.readAllBytes(scriptPath(filename));
        } catch (IOException e) {
            throw new UncheckedIOException("Failed to read script file", e);
        }
    }

    public void appendLog(String filename, String line) {
        try {
            Files.writeString(logPath(filename), line,
                    StandardCharsets.UTF_8,
                    StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (IOException e) {
            throw new UncheckedIOException("Failed to write log file", e);
        }
    }

    public String readLogContent(String filename) {
        try {
            Path p = logPath(filename);
            return Files.exists(p) ? Files.readString(p, StandardCharsets.UTF_8) : "";
        } catch (IOException e) {
            throw new UncheckedIOException("Failed to read log file", e);
        }
    }
}

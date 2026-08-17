package com.autorun.config;

import com.autorun.model.Role;
import com.autorun.model.Script;
import com.autorun.model.ScriptParam;
import com.autorun.model.User;
import com.autorun.repository.ScriptRepository;
import com.autorun.repository.UserRepository;
import com.autorun.service.StorageService;
import com.autorun.util.JsonUtil;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.core.io.Resource;
import org.springframework.core.io.support.PathMatchingResourcePatternResolver;
import org.springframework.core.io.support.ResourcePatternResolver;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

@Component
public class DataInitializer implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(DataInitializer.class);

    private static final Map<String, ScriptTemplate> TEMPLATES = Map.of(
            "system_info", new ScriptTemplate("system_info.cmd", "Cross-platform system info (demo)",
                    "system-info,demo", List.of()),
            "collect_logs", new ScriptTemplate("collect_logs.py", "Collect log files and summarize (demo)",
                    "log-collection,demo", List.of(new ScriptParam("days", "Days back", "Only consider logs newer than N days", false, "7"))),
            "backup", new ScriptTemplate("backup.sh", "Tar backup of a directory (Linux)",
                    "backup,linux", List.of(new ScriptParam("src", "Source directory", "Directory to archive", true, "/var/www"),
                    new ScriptParam("dest", "Destination", "Where to write the .tar.gz", true, "./backups"))),
            "patch_apt", new ScriptTemplate("patch_apt.sh", "APT update & upgrade (Linux)",
                    "patching,linux", List.of()),
            "add_user", new ScriptTemplate("add_user.sh", "Provision a new Linux user (Linux)",
                    "user-provisioning,identity,linux", List.of(new ScriptParam("username", "Username", "Login name for the new user", true, null))),
            "disk_usage", new ScriptTemplate("disk_usage.py", "Cross-platform disk usage report",
                    "disk,monitoring,cross-platform", List.of(new ScriptParam("path", "Path", "Directory to check (default: /)", false, "/"))),
            "check_services", new ScriptTemplate("check_services.sh", "Check status of system services (Linux)",
                    "services,monitoring,linux", List.of(new ScriptParam("services", "Services", "Comma-separated service names to check", true, null))),
            "cleanup_temp", new ScriptTemplate("cleanup_temp.sh", "Remove old temporary files (Linux)",
                    "cleanup,maintenance,linux", List.of(new ScriptParam("path", "Path", "Directory to clean (default: /tmp)", false, "/tmp"),
                    new ScriptParam("days", "Days old", "Delete files older than N days", false, "7"))),
            "ssl_check", new ScriptTemplate("ssl_check.py", "Check SSL certificate expiry dates",
                    "ssl,security,cross-platform", List.of(new ScriptParam("hosts", "Hosts", "Comma-separated host:port pairs", true, null),
                    new ScriptParam("warn_days", "Warning days", "Warn if certificate expires within N days", false, "30"))),
            "restart_process", new ScriptTemplate("restart_process.py", "Restart a process by name",
                    "process,operations,cross-platform", List.of(new ScriptParam("process_name", "Process name", "Name of the process/service to restart", true, null),
                    new ScriptParam("method", "Method", "Restart method: auto, systemctl, kill, taskkill", false, "auto"))));

    private final UserRepository userRepository;
    private final ScriptRepository scriptRepository;
    private final StorageService storageService;
    private final PasswordEncoder passwordEncoder;

    public DataInitializer(UserRepository userRepository,
                           ScriptRepository scriptRepository,
                           StorageService storageService,
                           PasswordEncoder passwordEncoder) {
        this.userRepository = userRepository;
        this.scriptRepository = scriptRepository;
        this.storageService = storageService;
        this.passwordEncoder = passwordEncoder;
    }

    @Override
    public void run(String... args) throws Exception {
        seedUsers();
        seedScripts();
    }

    private void seedUsers() {
        if (userRepository.count() == 0) {
            userRepository.save(new User("admin", passwordEncoder.encode("admin123"),
                    "System Admin", "admin@example.com", Role.ADMIN));
            userRepository.save(new User("tech", passwordEncoder.encode("tech123"),
                    "Support Technician", "tech@example.com", Role.TECH));
            log.info("Seeded default users: admin/admin123, tech/tech123");
        }
    }

    private void seedScripts() {
        ResourcePatternResolver resolver = new PathMatchingResourcePatternResolver();
        for (Map.Entry<String, ScriptTemplate> entry : TEMPLATES.entrySet()) {
            String scriptName = entry.getKey();
            ScriptTemplate template = entry.getValue();
            if (scriptRepository.existsByName(scriptName)) {
                continue;
            }
            try {
                Resource resource = resolver.getResource("classpath:scripts/" + template.filename());
                if (!resource.exists()) {
                    log.warn("Bundled script not found on classpath: {}", template.filename());
                    continue;
                }
                byte[] bytes = resource.getInputStream().readAllBytes();
                String filename = template.filename();
                storageService.writeScript(filename, bytes);
                User admin = userRepository.findByUsername("admin").orElse(null);
                Script script = new Script();
                script.setName(scriptName);
                script.setFilename(filename);
                script.setFileType(com.autorun.model.FileType.fromFilename(filename));
                script.setDescription(template.description());
                script.setTags(template.tags());
                script.setParametersJson(JsonUtil.serializeParams(template.params()));
                script.setSizeBytes((long) bytes.length);
                script.setStoragePath(storageService.scriptPath(filename).toString());
                script.setCreatedBy(admin);
                scriptRepository.save(script);
                log.info("Seeded sample script: {}", scriptName);
            } catch (IOException e) {
                log.warn("Failed to seed script {}: {}", scriptName, e.getMessage());
            }
        }
    }

    private record ScriptTemplate(String filename, String description, String tags, List<ScriptParam> params) {
    }
}

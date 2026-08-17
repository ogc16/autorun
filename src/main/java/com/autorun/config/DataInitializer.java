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
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Component
public class DataInitializer implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(DataInitializer.class);

    private static final Map<String, ScriptTemplate> TEMPLATES;
    static {
        TEMPLATES = new HashMap<>();
        // Core scripts
        TEMPLATES.put("system_info", new ScriptTemplate("system_info.cmd", "Cross-platform system info (demo)",
                "system-info,demo", List.of()));
        TEMPLATES.put("collect_logs", new ScriptTemplate("collect_logs.py", "Collect log files and summarize (demo)",
                "log-collection,demo", List.of(new ScriptParam("days", "Days back", "Only consider logs newer than N days", false, "7"))));
        TEMPLATES.put("backup", new ScriptTemplate("backup.sh", "Tar backup of a directory (Linux)",
                "backup,linux", List.of(new ScriptParam("src", "Source directory", "Directory to archive", true, "/var/www"),
                new ScriptParam("dest", "Destination", "Where to write the .tar.gz", true, "./backups"))));
        TEMPLATES.put("add_user", new ScriptTemplate("add_user.sh", "Provision a new Linux user (Linux)",
                "user-provisioning,identity,linux", List.of(new ScriptParam("username", "Username", "Login name for the new user", true, null))));
        TEMPLATES.put("disk_usage", new ScriptTemplate("disk_usage.py", "Cross-platform disk usage report",
                "disk,monitoring,cross-platform", List.of(new ScriptParam("path", "Path", "Directory to check (default: /)", false, "/"))));
        TEMPLATES.put("check_services", new ScriptTemplate("check_services.sh", "Check status of system services (Linux)",
                "services,monitoring,linux", List.of(new ScriptParam("services", "Services", "Comma-separated service names to check", true, null))));
        TEMPLATES.put("cleanup_temp", new ScriptTemplate("cleanup_temp.sh", "Remove old temporary files (Linux)",
                "cleanup,maintenance,linux", List.of(new ScriptParam("path", "Path", "Directory to clean (default: /tmp)", false, "/tmp"),
                new ScriptParam("days", "Days old", "Delete files older than N days", false, "7"))));
        TEMPLATES.put("ssl_check", new ScriptTemplate("ssl_check.py", "Check SSL certificate expiry dates",
                "ssl,security,cross-platform", List.of(new ScriptParam("hosts", "Hosts", "Comma-separated host:port pairs", true, null),
                new ScriptParam("warn_days", "Warning days", "Warn if certificate expires within N days", false, "30"))));
        TEMPLATES.put("restart_process", new ScriptTemplate("restart_process.py", "Restart a process by name",
                "process,operations,cross-platform", List.of(new ScriptParam("process_name", "Process name", "Name of the process/service to restart", true, null),
                new ScriptParam("method", "Method", "Restart method: auto, systemctl, kill, taskkill", false, "auto"))));
        // Patch management
        TEMPLATES.put("patch_apt", new ScriptTemplate("patch_apt.sh", "APT update & upgrade (Linux)",
                "patching,linux", List.of()));
        TEMPLATES.put("win_patch", new ScriptTemplate("win_patch.ps1", "Windows Update: check, install, auto-reboot (Windows)",
                "patching,windows", List.of()));
        TEMPLATES.put("linux_patch", new ScriptTemplate("linux_patch.sh", "Linux apt/yum upgrade with logging (Linux)",
                "patching,linux", List.of()));
        TEMPLATES.put("thirdparty_patch", new ScriptTemplate("thirdparty_patch.py", "Upgrade pip/npm packages (cross-platform)",
                "patching,cross-platform", List.of()));
        TEMPLATES.put("patch_verify", new ScriptTemplate("patch_verify.py", "Verify installed versions after patching",
                "patching,compliance,cross-platform", List.of()));
        TEMPLATES.put("patch_rollback", new ScriptTemplate("patch_rollback.py", "Rollback a package to a previous version",
                "patching,rollback,cross-platform", List.of(new ScriptParam("package", "Package", "Package name to rollback", true, null),
                new ScriptParam("version", "Version", "Target version to install", true, null))));
        TEMPLATES.put("patch_inventory", new ScriptTemplate("patch_inventory.py", "Full patch inventory across platforms",
                "patching,inventory,cross-platform", List.of()));
        TEMPLATES.put("patch_compliance", new ScriptTemplate("patch_compliance.py", "Check patch compliance against baseline",
                "patching,compliance,cross-platform", List.of()));
        // System & Infrastructure
        TEMPLATES.put("health_check", new ScriptTemplate("health_check.py", "Cross-platform health: CPU, disk, memory, load",
                "monitoring,health,cross-platform", List.of()));
        TEMPLATES.put("net_diag", new ScriptTemplate("net_diag.py", "Network diagnostics: DNS, ping, ports, routes",
                "networking,diagnostics,cross-platform", List.of()));
        TEMPLATES.put("svc_monitor", new ScriptTemplate("svc_monitor.py", "Service/process monitor with restart",
                "monitoring,services,cross-platform", List.of(new ScriptParam("services", "Services", "Comma-separated service names to monitor", true, null))));
        // Patch orchestration & reporting
        TEMPLATES.put("patch_orchestrator", new ScriptTemplate("patch_orchestrator.py", "Master daily patch workflow: inventory, apply, verify, report, notify",
                "patching,orchestration,cross-platform", List.of(
                new ScriptParam("dry_run", "Dry run", "Only check, never install (default: false)", false, "false"),
                new ScriptParam("auto_rollback", "Auto rollback", "Auto-revert on verification failure (default: true)", false, "true"),
                new ScriptParam("notify", "Notify", "Send notification at end (default: false)", false, "false"),
                new ScriptParam("slack_webhook", "Slack webhook", "Slack webhook URL", false, ""),
                new ScriptParam("email_to", "Email to", "Email recipient", false, ""))));
        TEMPLATES.put("daily_report", new ScriptTemplate("daily_report.py", "Aggregate system health, patches, backups into one report",
                "reporting,compliance,cross-platform", List.of(
                new ScriptParam("output", "Output format", "json, text, or html (default: text)", false, "text"),
                new ScriptParam("sections", "Sections", "health, patches, backups, security, alerts (default: all)", false, "all"))));
        TEMPLATES.put("notify", new ScriptTemplate("notify.py", "Send alerts via email or Slack",
                "notifications,cross-platform", List.of(
                new ScriptParam("channel", "Channel", "slack, email, or both (default: both)", false, "both"),
                new ScriptParam("title", "Title", "Alert title", true, null),
                new ScriptParam("body", "Body", "Alert body text", true, null),
                new ScriptParam("severity", "Severity", "info, warning, or critical (default: warning)", false, "warning"),
                new ScriptParam("slack_webhook", "Slack webhook", "Slack webhook URL", false, ""),
                new ScriptParam("email_to", "Email to", "Email recipient", false, ""))));
        // Tool integrations
        TEMPLATES.put("ansible_runner", new ScriptTemplate("ansible_runner.py", "Run Ansible playbooks, ping hosts, inspect inventory",
                "ansible,provisioning,cross-platform", List.of(
                new ScriptParam("action", "Action", "run, list, inventory, ping, check (default: run)", false, "run"),
                new ScriptParam("playbook", "Playbook", "Path to playbook YAML", false, ""),
                new ScriptParam("inventory", "Inventory", "Inventory file path or host list", true, null),
                new ScriptParam("limit", "Limit", "Limit to specific hosts", false, ""),
                new ScriptParam("tags", "Tags", "Run only specific tags", false, ""),
                new ScriptParam("extra_vars", "Extra vars", "JSON string of extra variables", false, "{}"),
                new ScriptParam("become", "Become", "Use sudo escalation (default: true)", false, "true"),
                new ScriptParam("check_mode", "Check mode", "Dry-run (default: false)", false, "false"),
                new ScriptParam("verbosity", "Verbosity", "Verbosity level 0-4 (default: 0)", false, "0"),
                new ScriptParam("ssh_key", "SSH key", "Path to SSH private key", false, ""))));
        TEMPLATES.put("power_automate", new ScriptTemplate("power_automate.py", "Microsoft 365 automation via Graph API",
                "microsoft,automate,business", List.of(
                new ScriptParam("action", "Action", "create_user, list_users, disable_user, assign_license, send_teams_message, send_email, list_sharepoint_files, list_groups, add_to_group", true, null),
                new ScriptParam("user_email", "User email", "Target user email", false, ""),
                new ScriptParam("display_name", "Display name", "User display name (create_user)", false, ""),
                new ScriptParam("password", "Password", "Initial password (create_user)", false, ""),
                new ScriptParam("license_sku", "License SKU", "License SKU ID (assign_license)", false, ""),
                new ScriptParam("message", "Message", "Message text or subject|body", false, ""),
                new ScriptParam("channel_id", "Channel ID", "Teams channel ID", false, ""))));
        TEMPLATES.put("datto_rmm", new ScriptTemplate("datto_rmm.py", "Datto RMM: devices, patches, scripts, alerts, audit",
                "rmm,monitoring,multi-client", List.of(
                new ScriptParam("action", "Action", "list_devices, list_sites, get_device, run_script, list_patches, install_patch, get_alerts, get_audit_log, list_scripts", true, null),
                new ScriptParam("site_uid", "Site UID", "Filter by site UID", false, ""),
                new ScriptParam("device_uid", "Device UID", "Device UID for device actions", false, ""),
                new ScriptParam("script_uid", "Script UID", "Script UID for run_script", false, ""),
                new ScriptParam("patch_uid", "Patch UID", "Patch UID for install_patch", false, ""),
                new ScriptParam("query", "Query", "Search query for devices", false, ""))));
        TEMPLATES.put("zapier_trigger", new ScriptTemplate("zapier_trigger.py", "Trigger Zapier webhooks to connect thousands of apps",
                "zapier,workflow,automate", List.of(
                new ScriptParam("action", "Action", "trigger, test_webhook, execution_complete, alert, patch_report", false, "trigger"),
                new ScriptParam("webhook_url", "Webhook URL", "Zapier webhook URL", true, null),
                new ScriptParam("zap_name", "Zap name", "Friendly name for the event", false, "AutoRun Event"),
                new ScriptParam("event_type", "Event type", "execution_complete, alert, patch_report, health_check, custom", false, "custom"),
                new ScriptParam("payload", "Payload", "JSON string of data to send", false, "{}"),
                new ScriptParam("priority", "Priority", "low, normal, high, critical", false, "normal"))));
        TEMPLATES.put("anydesk_admin", new ScriptTemplate("anydesk_admin.py", "AnyDesk remote access: sessions, devices, unattended access",
                "anydesk,remote-access,admin", List.of(
                new ScriptParam("action", "Action", "get_adr_id, get_status, list_devices, set_password, disconnect_all, set_alias, get_logs, unattended_access, session_record", true, null),
                new ScriptParam("password", "Password", "AnyDesk unattended access password", false, ""),
                new ScriptParam("device_id", "Device ID", "Target device AnyDesk ID", false, ""),
                new ScriptParam("alias", "Alias", "Friendly alias for this device", false, ""),
                new ScriptParam("duration", "Duration", "Recording duration in minutes (0=unlimited)", false, "0"))));
    }

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

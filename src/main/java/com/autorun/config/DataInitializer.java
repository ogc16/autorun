package com.autorun.config;

import com.autorun.model.*;
import com.autorun.repository.ScriptRepository;
import com.autorun.repository.UserRepository;
import com.autorun.repository.WorkflowRepository;
import com.autorun.service.StorageService;
import com.autorun.service.WorkflowService;
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
import java.util.ArrayList;
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
        // ── Accounting & Compliance ──────────────────────────────────────────
        TEMPLATES.put("bank_feed_sync", new ScriptTemplate("bank_feed_sync.py", "Bank Feed Sync & Reconciliation",
                "accounting,reconciliation,finance", List.of(
                new ScriptParam("institution", "Institution", "Bank name (e.g. Chase, Revolut)", false, "Default Bank"),
                new ScriptParam("account", "Account", "Account identifier", false, "CHECKING-001"),
                new ScriptParam("days", "Days back", "Days to look back for transactions", false, "30"),
                new ScriptParam("tolerance", "Tolerance", "Auto-match tolerance in currency units", false, "0.01"))));
        TEMPLATES.put("intercompany_clearing", new ScriptTemplate("intercompany_clearing.py", "Intercompany Clearing & Elimination",
                "accounting,consolidation,finance", List.of(
                new ScriptParam("period", "Period", "Reporting period (YYYY-MM)", false, ""),
                new ScriptParam("entities", "Entities", "Comma-separated entity codes", false, "ALL"))));
        TEMPLATES.put("depreciation_run", new ScriptTemplate("depreciation_run.py", "Depreciation & Amortization Run",
                "accounting,assets,finance", List.of(
                new ScriptParam("period", "Period", "Reporting period (YYYY-MM)", false, ""),
                new ScriptParam("method", "Method", "SL (straight-line), DB (declining balance), SYD (sum-of-years), MACRS", false, "SL"),
                new ScriptParam("category", "Category", "Filter by asset category", false, "ALL"))));
        TEMPLATES.put("fx_revaluation", new ScriptTemplate("fx_revaluation.py", "FX Revaluation with ECB Rates",
                "accounting,fx,finance", List.of(
                new ScriptParam("base_currency", "Base currency", "Functional currency for revaluation", false, "EUR"),
                new ScriptParam("period", "Period", "Reporting period (YYYY-MM)", false, ""),
                new ScriptParam("tolerance", "Tolerance", "Materiality threshold for exceptions", false, "100.00"))));
        TEMPLATES.put("vat_gst_return", new ScriptTemplate("vat_gst_return.py", "VAT/GST Return Pre-Compilation",
                "accounting,tax,compliance", List.of(
                new ScriptParam("country", "Country", "Jurisdiction code (GB, IE, DE, AU, NZ, SG)", false, "GB"),
                new ScriptParam("period", "Period", "Tax period (YYYY-MM or YYYY-Q1)", false, ""),
                new ScriptParam("scheme", "Scheme", "Tax scheme (standard, flat-rate, cash-accounting)", false, "standard"))));
        TEMPLATES.put("audit_extract", new ScriptTemplate("audit_extract.py", "Audit Trail & Fixed Asset Archive",
                "accounting,audit,compliance", List.of(
                new ScriptParam("start_date", "Start date", "Audit trail start (YYYY-MM-DD)", false, ""),
                new ScriptParam("end_date", "End date", "Audit trail end (YYYY-MM-DD)", false, ""),
                new ScriptParam("asset_id", "Asset ID", "Specific fixed asset to archive", false, "ALL"),
                new ScriptParam("hash_chain", "Hash chain", "Verify Merkle chain integrity", false, "true"))));
        TEMPLATES.put("payment_batch", new ScriptTemplate("payment_batch.py", "Batch Payment File Generation (ISO 20022)",
                "accounting,payments,finance", List.of(
                new ScriptParam("batch_id", "Batch ID", "Payment batch identifier", false, ""),
                new ScriptParam("format", "Format", "ISO_20022_XML, SEPA_XML, BACS_TXT", false, "ISO_20022_XML"),
                new ScriptParam("currency", "Currency", "Payment currency code", false, "EUR"),
                new ScriptParam("execute", "Execute", "Create actual file (false = preview)", false, "false"))));
        TEMPLATES.put("dunning_credit_control", new ScriptTemplate("dunning_credit_control.py", "Dunning & Credit Control",
                "accounting,credit-control,finance", List.of(
                new ScriptParam("aging_buckets", "Aging buckets", "Comma-separated day thresholds", false, "30,60,90,120"),
                new ScriptParam("dunning_level", "Dunning level", "1=reminder, 2=firm, 3=final, 4=legal", false, "1"),
                new ScriptParam("auto_credit_hold", "Auto credit hold", "Auto-hold accounts over limit", false, "true"))));
        // ── FP&A ────────────────────────────────────────────────────────────
        TEMPLATES.put("bva_variance", new ScriptTemplate("bva_variance.py", "Budget vs. Actuals Variance Analysis",
                "fp&a,variance,planning", List.of(
                new ScriptParam("period", "Period", "Reporting period (YYYY-MM)", false, ""),
                new ScriptParam("threshold_pct", "Threshold %", "Flag variances above this %", false, "10"),
                new ScriptParam("by_cost_center", "By cost center", "Break down by cost center", false, "true"))));
        TEMPLATES.put("rolling_forecast", new ScriptTemplate("rolling_forecast.py", "Rolling Forecast Engine",
                "fp&a,forecast,planning", List.of(
                new ScriptParam("horizon", "Horizon", "Forecast months ahead", false, "12"),
                new ScriptParam("method", "Method", "linear, exponential_smoothing, moving_avg", false, "linear"),
                new ScriptParam("smooth_alpha", "Alpha", "Smoothing factor (0-1) for exponential method", false, "0.3"))));
        TEMPLATES.put("saas_metrics", new ScriptTemplate("saas_metrics.py", "SaaS Metrics & Unit Economics",
                "fp&a,saas,startup", List.of(
                new ScriptParam("period", "Period", "Reporting period (YYYY-MM)", false, ""),
                new ScriptParam("cohort_months", "Cohort months", "Number of months for cohort analysis", false, "12"),
                new ScriptParam("churn_window", "Churn window", "Days to look for churn signals", false, "90"))));
        TEMPLATES.put("board_deck_gen", new ScriptTemplate("board_deck_gen.py", "Board Pack & KPI Narrative Generator",
                "fp&a,reporting,board", List.of(
                new ScriptParam("period", "Period", "Reporting period (YYYY-MM)", false, ""),
                new ScriptParam("sections", "Sections", "kpi_summary, p_and_l, balance_sheet, cashflow, variance, forecasts", false, "all"),
                new ScriptParam("format", "Format", "json, html, text", false, "json"),
                new ScriptParam("audience", "Audience", "board, cfo, investors", false, "board"))));
    }

    private final UserRepository userRepository;
    private final ScriptRepository scriptRepository;
    private final WorkflowRepository workflowRepository;
    private final WorkflowService workflowService;
    private final StorageService storageService;
    private final PasswordEncoder passwordEncoder;

    public DataInitializer(UserRepository userRepository,
                           ScriptRepository scriptRepository,
                           WorkflowRepository workflowRepository,
                           WorkflowService workflowService,
                           StorageService storageService,
                           PasswordEncoder passwordEncoder) {
        this.userRepository = userRepository;
        this.scriptRepository = scriptRepository;
        this.workflowRepository = workflowRepository;
        this.workflowService = workflowService;
        this.storageService = storageService;
        this.passwordEncoder = passwordEncoder;
    }

    @Override
    public void run(String... args) throws Exception {
        seedUsers();
        seedScripts();
        seedWorkflows();
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

    private void seedWorkflows() {
        if (workflowRepository.count() > 0) {
            return;
        }
        User admin = userRepository.findByUsername("admin").orElse(null);
        if (admin == null) return;

        // ── Monthly Finance Close ───────────────────────────────────────────
        seedWorkflow(admin, "Monthly Finance Close",
                "Full month-end close: bank reconciliation, FX revaluation, depreciation, intercompany clearing, VAT/GST return, dunning review, and variance analysis.",
                "finance,month-end,compliance",
                List.of("bank_feed_sync", "fx_revaluation", "depreciation_run", "intercompany_clearing",
                        "vat_gst_return", "dunning_credit_control", "bva_variance"));

        // ── Quarterly Audit Pack ────────────────────────────────────────────
        seedWorkflow(admin, "Quarterly Audit Pack",
                "Generate the quarterly audit trail archive, fixed asset extract, and board-ready KPI narrative for external auditors.",
                "finance,audit,quarterly",
                List.of("audit_extract", "depreciation_run", "intercompany_clearing", "board_deck_gen"));

        // ── Payment Run ─────────────────────────────────────────────────────
        seedWorkflow(admin, "AP Payment Run",
                "Reconcile bank feed, generate ISO 20022 payment batch file, and preview before submission.",
                "finance,payments,ap",
                List.of("bank_feed_sync", "payment_batch"));

        // ── SaaS Board Pack ────────────────────────────────────────────────
        seedWorkflow(admin, "SaaS Board Pack",
                "Pull SaaS unit economics, run rolling forecast, and generate board-ready KPI narrative.",
                "fp&a,saas,board",
                List.of("saas_metrics", "rolling_forecast", "board_deck_gen"));

        log.info("Seeded 4 finance workflows");
    }

    private void seedWorkflow(User user, String name, String description, String tags,
                              List<String> scriptNames) {
        List<WorkflowStep> steps = new ArrayList<>();
        int order = 1;
        for (String scriptName : scriptNames) {
            Script script = scriptRepository.findByName(scriptName).orElse(null);
            if (script == null) {
                log.warn("Workflow '{}' references unknown script '{}', skipping step", name, scriptName);
                continue;
            }
            WorkflowStep step = new WorkflowStep();
            step.setScriptId(script.getId());
            step.setName(scriptName);
            step.setOrder(order++);
            step.setOnError(WorkflowStepOnError.STOP);
            step.setTimeoutSeconds(600);
            step.setParamsJson("{}");
            steps.add(step);
        }
        if (!steps.isEmpty()) {
            workflowService.create(user, name, description, tags, steps, true);
            log.info("Seeded workflow '{}' with {} steps", name, steps.size());
        }
    }

    private record ScriptTemplate(String filename, String description, String tags, List<ScriptParam> params) {
    }
}

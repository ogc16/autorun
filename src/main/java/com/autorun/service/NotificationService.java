package com.autorun.service;

import com.autorun.model.ExecutionLog;
import com.autorun.model.ExecutionStatus;
import com.autorun.model.NotificationSettings;
import com.autorun.repository.NotificationSettingsRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.client.RestClient;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class NotificationService {

    private static final Logger log = LoggerFactory.getLogger(NotificationService.class);

    private final NotificationSettingsRepository settingsRepository;
    private final JavaMailSender mailSender;
    private final StorageService storageService;
    private final RestClient restClient;
    private final String smtpHost;

    public NotificationService(NotificationSettingsRepository settingsRepository,
                               JavaMailSender mailSender,
                               StorageService storageService,
                               @Value("${spring.mail.host:}") String smtpHost) {
        this.settingsRepository = settingsRepository;
        this.mailSender = mailSender;
        this.storageService = storageService;
        this.smtpHost = smtpHost;
        this.restClient = RestClient.builder().build();
    }

    public NotificationSettings getSettings() {
        return settingsRepository.findById(1L).orElseGet(() -> {
            NotificationSettings s = new NotificationSettings();
            settingsRepository.save(s);
            return s;
        });
    }

    public NotificationSettings saveSettings(NotificationSettings settings) {
        NotificationSettings current = getSettings();
        current.setEmailEnabled(settings.isEmailEnabled());
        current.setEmailRecipients(settings.getEmailRecipients());
        current.setSlackEnabled(settings.isSlackEnabled());
        current.setSlackWebhookUrl(settings.getSlackWebhookUrl());
        current.setSlackChannel(settings.getSlackChannel());
        return settingsRepository.save(current);
    }

    public void notifyExecution(ExecutionLog execution, String notifyOn) {
        if (notifyOn == null || "NEVER".equals(notifyOn)) {
            return;
        }
        boolean failed = execution.getStatus() == ExecutionStatus.FAILED
                || execution.getStatus() == ExecutionStatus.TIMEOUT;
        boolean shouldSend = "ALWAYS".equals(notifyOn) || ("FAILURE".equals(notifyOn) && failed);
        if (!shouldSend) {
            return;
        }
        sendAlert(execution);
    }

    private void sendAlert(ExecutionLog execution) {
        NotificationSettings settings = getSettings();
        String title = executionTitle(execution);
        String body = executionBody(execution);

        if (settings.isSlackEnabled() && StringUtils.hasText(settings.getSlackWebhookUrl())) {
            sendSlack(settings, title, body);
        }
        if (settings.isEmailEnabled() && StringUtils.hasText(smtpHost)
                && StringUtils.hasText(settings.getEmailRecipients())) {
            sendEmail(settings, title, body, execution);
        }
        if (!settings.isSlackEnabled() && !settings.isEmailEnabled()) {
            log.info("Notification requested but disabled: {}", title);
        }
    }

    private void sendSlack(NotificationSettings settings, String title, String body) {
        try {
            Map<String, Object> payload = new LinkedHashMap<>();
            String channel = settings.getSlackChannel();
            if (StringUtils.hasText(channel)) {
                payload.put("channel", channel);
            }
            payload.put("text", title + "\n\n" + body);
            restClient.post()
                    .uri(settings.getSlackWebhookUrl())
                    .body(payload)
                    .retrieve()
                    .toBodilessEntity();
            log.info("Slack alert sent: {}", title);
        } catch (Exception e) {
            log.error("Slack alert failed: {}", e.getMessage());
        }
    }

    private void sendEmail(NotificationSettings settings, String title, String body, ExecutionLog execution) {
        try {
            List<String> recipients = List.of(settings.getEmailRecipients().split("[,\\s]+"))
                    .stream().filter(StringUtils::hasText).collect(Collectors.toList());
            SimpleMailMessage msg = new SimpleMailMessage();
            msg.setTo(recipients.toArray(String[]::new));
            msg.setSubject("[AutoRun] " + title);
            String logPath = storageService.logPath("execution-" + execution.getId() + ".log").toString();
            msg.setText(body + "\n\nLog file: " + logPath);
            mailSender.send(msg);
            log.info("Email alert sent to {}", recipients);
        } catch (Exception e) {
            log.error("Email alert failed: {}", e.getMessage());
        }
    }

    public Map<String, String> sendTest(String channel) {
        NotificationSettings settings = getSettings();
        Map<String, String> report = new LinkedHashMap<>();
        boolean slack = "all".equalsIgnoreCase(channel) || "slack".equalsIgnoreCase(channel);
        boolean email = "all".equalsIgnoreCase(channel) || "email".equalsIgnoreCase(channel);

        if (slack) {
            if (settings.isSlackEnabled() && StringUtils.hasText(settings.getSlackWebhookUrl())) {
                sendSlack(settings, "Test alert from AutoRun", "This is a test Slack notification.");
                report.put("slack", "sent");
            } else {
                report.put("slack", "disabled");
            }
        }
        if (email) {
            if (settings.isEmailEnabled() && StringUtils.hasText(smtpHost)
                    && StringUtils.hasText(settings.getEmailRecipients())) {
                sendEmail(settings, "Test alert from AutoRun", "This is a test email notification.", null);
                report.put("email", "sent");
            } else {
                report.put("email", "disabled (no SMTP host or recipients)");
            }
        }
        return report;
    }

    private String executionTitle(ExecutionLog execution) {
        String status = execution.getStatus().name();
        String script = execution.getScript() != null ? execution.getScript().getName() : "unknown";
        String job = execution.getJob() != null ? " [job: " + execution.getJob().getName() + "]" : "";
        return "Execution #%d %s - script '%s'%s".formatted(execution.getId(), status, script, job);
    }

    private String executionBody(ExecutionLog execution) {
        return "Script: %s\nTriggered by: %s\nStatus: %s\nExit code: %s\nStarted: %s\nFinished: %s\nDuration: %d ms"
                .formatted(
                        execution.getScript() != null ? execution.getScript().getName() : "unknown",
                        execution.getTriggeredBy(),
                        execution.getStatus(),
                        execution.getExitCode() == null ? "-" : execution.getExitCode(),
                        execution.getStartedAt(),
                        execution.getFinishedAt(),
                        execution.getDurationMs() == null ? 0 : execution.getDurationMs());
    }
}

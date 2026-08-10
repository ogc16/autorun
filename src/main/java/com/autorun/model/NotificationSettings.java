package com.autorun.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "notification_settings")
@Getter
@Setter
@NoArgsConstructor
public class NotificationSettings {

    @Id
    private Long id = 1L;

    @Column(name = "email_enabled", nullable = false)
    private boolean emailEnabled = false;

    @Column(name = "email_recipients", length = 2000)
    private String emailRecipients;

    @Column(name = "slack_enabled", nullable = false)
    private boolean slackEnabled = false;

    @Column(name = "slack_webhook", length = 512)
    private String slackWebhookUrl;

    @Column(name = "slack_channel", length = 128)
    private String slackChannel;
}

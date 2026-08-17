package com.autorun.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDateTime;

@Entity
@Table(name = "policies")
@Getter
@Setter
@NoArgsConstructor
public class Policy {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, nullable = false, length = 128)
    private String name;

    @Column(length = 2000)
    private String description;

    @ManyToOne
    private ClientGroup clientGroup;

    @ManyToOne
    private Script script;

    @Column(name = "cron_expression", nullable = false, length = 64)
    private String cronExpression;

    @Column(name = "time_zone", length = 64)
    private String timeZone = "UTC";

    @Column(nullable = false)
    private boolean enabled = true;

    @Column(name = "arguments_json", length = 4000)
    private String argumentsJson;

    @Column(name = "notify_on", length = 16)
    private String notifyOn = "FAILURE";

    @ManyToOne
    private User createdBy;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "last_run_at")
    private LocalDateTime lastRunAt;
}

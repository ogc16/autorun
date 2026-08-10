package com.autorun.model;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Lob;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDateTime;

@Entity
@Table(name = "execution_logs")
@Getter
@Setter
@NoArgsConstructor
public class ExecutionLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne
    private Script script;

    @Enumerated(EnumType.STRING)
    @Column(name = "triggered_by", nullable = false, length = 16)
    private TriggerType triggeredBy;

    @ManyToOne
    private User user;

    @ManyToOne
    private ScriptJob job;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 16)
    private ExecutionStatus status;

    @Column(name = "exit_code")
    private Integer exitCode;

    @Column(name = "started_at", nullable = false)
    private LocalDateTime startedAt = LocalDateTime.now();

    @Column(name = "finished_at")
    private LocalDateTime finishedAt;

    @Column(name = "duration_ms")
    private Long durationMs;

    @JsonIgnore
    @Lob
    @Column(name = "log_content")
    private String logContent;

    @JsonIgnore
    @Column(name = "log_file", length = 512)
    private String logFile;

    @Column(name = "arguments_json", length = 4000)
    private String argumentsJson;

    @Column(name = "notify_on", length = 16)
    private String notifyOn = "FAILURE";

    @Column(name = "error_message", length = 2000)
    private String errorMessage;
}

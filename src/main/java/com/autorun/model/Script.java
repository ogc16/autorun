package com.autorun.model;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
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
@Table(name = "scripts")
@Getter
@Setter
@NoArgsConstructor
public class Script {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, nullable = false, length = 128)
    private String name;

    @Column(nullable = false, length = 256)
    private String filename;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 16)
    private FileType fileType;

    @Column(length = 2000)
    private String description;

    @Column(length = 512)
    private String tags;

    @Column(name = "parameters_json", length = 4000)
    private String parametersJson;

    @Column(name = "size_bytes")
    private Long sizeBytes;

    @JsonIgnore
    @Column(name = "storage_path", nullable = false, length = 512)
    private String storagePath;

    @ManyToOne
    private User createdBy;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @Column(name = "last_executed_at")
    private LocalDateTime lastExecutedAt;
}

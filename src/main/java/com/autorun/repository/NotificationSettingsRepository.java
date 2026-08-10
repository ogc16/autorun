package com.autorun.repository;

import com.autorun.model.NotificationSettings;
import org.springframework.data.jpa.repository.JpaRepository;

public interface NotificationSettingsRepository extends JpaRepository<NotificationSettings, Long> {
}

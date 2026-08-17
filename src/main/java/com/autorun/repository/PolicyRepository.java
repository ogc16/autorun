package com.autorun.repository;

import com.autorun.model.Policy;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface PolicyRepository extends JpaRepository<Policy, Long> {
    boolean existsByName(String name);
    List<Policy> findByEnabledTrue();
    List<Policy> findByClientGroupId(Long clientGroupId);
}

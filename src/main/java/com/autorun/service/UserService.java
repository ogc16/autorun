package com.autorun.service;

import com.autorun.config.ConflictException;
import com.autorun.config.ResourceNotFoundException;
import com.autorun.model.Role;
import com.autorun.model.User;
import com.autorun.repository.UserRepository;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class UserService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    public UserService(UserRepository userRepository, PasswordEncoder passwordEncoder) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
    }

    @Transactional(readOnly = true)
    public List<User> list(String search) {
        List<User> users = userRepository.findAll();
        if (search != null && !search.isBlank()) {
            String q = search.toLowerCase();
            users.removeIf(u -> !(u.getUsername() != null && u.getUsername().toLowerCase().contains(q)
                    || u.getEmail() != null && u.getEmail().toLowerCase().contains(q)
                    || u.getDisplayName() != null && u.getDisplayName().toLowerCase().contains(q)));
        }
        users.sort((a, b) -> a.getUsername().compareToIgnoreCase(b.getUsername()));
        return users;
    }

    @Transactional
    public User create(String username, String password, String displayName, String email, Role role) {
        if (username == null || username.isBlank() || password == null || password.isBlank()) {
            throw new IllegalArgumentException("Username and password are required");
        }
        if (userRepository.existsByUsername(username.trim())) {
            throw new ConflictException("Username already exists: " + username);
        }
        if (email != null && !email.isBlank() && userRepository.existsByEmail(email.trim())) {
            throw new ConflictException("Email already in use: " + email);
        }
        User user = new User(username.trim(), passwordEncoder.encode(password), displayName, email,
                role == null ? Role.TECH : role);
        return userRepository.save(user);
    }

    @Transactional
    public User update(Long id, String displayName, String email, Role role, String newPassword) {
        User user = get(id);
        if (displayName != null) {
            user.setDisplayName(displayName);
        }
        if (email != null && !email.isBlank()) {
            user.setEmail(email.trim());
        }
        if (role != null) {
            user.setRole(role);
        }
        if (newPassword != null && !newPassword.isBlank()) {
            user.setPassword(passwordEncoder.encode(newPassword));
        }
        return userRepository.save(user);
    }

    @Transactional
    public void delete(Long id, User actor) {
        if (actor != null && actor.getId().equals(id)) {
            throw new IllegalArgumentException("You cannot delete your own account");
        }
        User user = get(id);
        user.setEnabled(false);
        userRepository.save(user);
    }

    public User get(Long id) {
        return userRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("User not found: " + id));
    }

    public User getByUsername(String username) {
        return userRepository.findByUsername(username)
                .orElseThrow(() -> new ResourceNotFoundException("User not found: " + username));
    }

    @Transactional
    public void recordLogin(User user) {
        user.setLastLoginAt(java.time.LocalDateTime.now());
        userRepository.save(user);
    }
}

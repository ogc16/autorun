package com.autorun.controller;

import com.autorun.model.User;
import com.autorun.model.Role;
import com.autorun.security.AppUserDetails;
import com.autorun.security.JwtUtil;
import com.autorun.service.AuditService;
import com.autorun.service.UserService;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthenticationManager authenticationManager;
    private final JwtUtil jwtUtil;
    private final UserService userService;
    private final AuditService auditService;

    public AuthController(AuthenticationManager authenticationManager,
                          JwtUtil jwtUtil,
                          UserService userService,
                          AuditService auditService) {
        this.authenticationManager = authenticationManager;
        this.jwtUtil = jwtUtil;
        this.userService = userService;
        this.auditService = auditService;
    }

    @PostMapping("/login")
    public ResponseEntity<Map<String, Object>> login(@RequestBody LoginRequest request,
                                                     HttpServletRequest http) {
        Authentication authentication = authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(request.username(), request.password()));

        AppUserDetails principal = (AppUserDetails) authentication.getPrincipal();
        User user = userService.get(principal.getId());
        userService.recordLogin(user);

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("accessToken", jwtUtil.generateAccessToken(user.getUsername(), user.getRole()));
        body.put("refreshToken", jwtUtil.generateRefreshToken(user.getUsername(), user.getRole()));
        body.put("tokenType", "Bearer");
        body.put("expiresIn", jwtUtil.getAccessTtlSeconds());
        body.put("user", user);

        auditService.record(user, "LOGIN", "AUTH", user.getId().toString(), "User logged in", http);
        return ResponseEntity.ok(body);
    }

    @PostMapping("/refresh")
    public ResponseEntity<Map<String, Object>> refresh(@RequestBody RefreshRequest request) {
        try {
            Claims claims = jwtUtil.parse(request.refreshToken());
            User user = userService.getByUsername(claims.getSubject());
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("accessToken", jwtUtil.generateAccessToken(user.getUsername(), user.getRole()));
            body.put("refreshToken", jwtUtil.generateRefreshToken(user.getUsername(), user.getRole()));
            body.put("tokenType", "Bearer");
            body.put("expiresIn", jwtUtil.getAccessTtlSeconds());
            body.put("user", user);
            return ResponseEntity.ok(body);
        } catch (JwtException | IllegalArgumentException e) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                    .body(Map.of("status", 401, "error", "Unauthorized", "message", "Invalid or expired token"));
        }
    }

    @GetMapping("/me")
    public User me(Authentication authentication) {
        AppUserDetails principal = (AppUserDetails) authentication.getPrincipal();
        return userService.get(principal.getId());
    }

    public record LoginRequest(String username, String password) {
    }

    public record RefreshRequest(String refreshToken) {
    }
}

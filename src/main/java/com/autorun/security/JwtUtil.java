package com.autorun.security;

import com.autorun.model.Role;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

@Component
public class JwtUtil {

    private final SecretKey key;
    private final long accessTtlSeconds;
    private final long refreshTtlSeconds;

    public JwtUtil(@Value("${autorun.jwt.secret}") String secret,
                   @Value("${autorun.jwt.access-token-ttl}") long accessTtlSeconds,
                   @Value("${autorun.jwt.refresh-token-ttl}") long refreshTtlSeconds) {
        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        this.accessTtlSeconds = accessTtlSeconds;
        this.refreshTtlSeconds = refreshTtlSeconds;
    }

    public String generateAccessToken(String username, Role role) {
        return buildToken(username, role, accessTtlSeconds);
    }

    public String generateRefreshToken(String username, Role role) {
        return buildToken(username, role, refreshTtlSeconds);
    }

    private String buildToken(String username, Role role, long ttlSeconds) {
        Date now = new Date();
        return Jwts.builder()
                .subject(username)
                .claim("role", role.name())
                .issuedAt(now)
                .expiration(new Date(now.getTime() + ttlSeconds * 1000))
                .signWith(key)
                .compact();
    }

    public Claims parse(String token) throws JwtException {
        return Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }

    public long getAccessTtlSeconds() {
        return accessTtlSeconds;
    }
}

package com.autorun.controller;

import com.autorun.model.Role;
import com.autorun.model.User;
import com.autorun.security.AppUserDetails;
import com.autorun.service.UserService;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/users")
public class UserApiController {

    private final UserService userService;

    public UserApiController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping
    @PreAuthorize("hasRole('ADMIN')")
    public List<User> list(@RequestParam(required = false) String search) {
        return userService.list(search);
    }

    @PostMapping
    @PreAuthorize("hasRole('ADMIN')")
    public User create(@RequestBody CreateUserRequest request) {
        return userService.create(request.username(), request.password(), request.displayName(),
                request.email(), request.role());
    }

    @PutMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public User update(@PathVariable Long id, @RequestBody UpdateUserRequest request) {
        return userService.update(id, request.displayName(), request.email(), request.role(), request.password());
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public void delete(@PathVariable Long id, Authentication authentication) {
        AppUserDetails principal = (AppUserDetails) authentication.getPrincipal();
        userService.delete(id, userService.get(principal.getId()));
    }

    public record CreateUserRequest(String username, String password, String displayName,
                                    String email, Role role) {
    }

    public record UpdateUserRequest(String displayName, String email, Role role, String password) {
    }
}

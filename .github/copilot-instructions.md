# Linux Ansible Playbooks - AI Agent Instructions

## Project Overview
This repository contains a collection of Ansible playbooks for Linux system administration and automation tasks. Each playbook handles specific configuration tasks targeting Ubuntu/Debian systems.

## Architecture & Components

### Playbook Structure
All playbooks follow a consistent pattern:
- **Hosts**: Target `all` hosts defined in inventory
- **Privileges**: Use `become: yes` for root-level operations
- **Tasks**: Linear execution of idempotent operations
- **Handlers**: Optional handlers for service restarts (e.g., `ssh-remove-passwd-auth.yaml`)

### Core Playbooks
- `apt-update-package.yaml` - Package management (cache updates, distribution upgrades)
- `ssh-send-pubkey.yaml` - SSH public key deployment using Ansible's authorized_key module
- `ssh-remove-passwd-auth.yaml` - Hardens SSH by disabling password authentication
- `ubuntu-add-sshkey.yaml` - Extended SSH setup with sudoers configuration (metadata format)

## Key Patterns & Conventions

### 1. **Ansible Module Usage**
- Use standard Ansible modules: `apt`, `lineinfile`, `ansible.posix.authorized_key`, `service`
- SSH configuration changes always target `/etc/ssh/sshd_config`
- Apply state changes with `state: present` (idempotent operations)

### 2. **Security Practices**
- All privileged tasks require `become: yes` for root access
- SSH hardening uses regex patterns in `lineinfile` (e.g., `'^#?PasswordAuthentication'`)
- Public keys loaded from files using `lookup('file', path)` pattern

### 3. **Handler Integration**
- Service restart operations use handlers (seen in `ssh-remove-passwd-auth.yaml`)
- Prevents unnecessary service restarts if configuration unchanged

### 4. **Naming Conventions**
- Task names use imperative verbs: "Désactiver", "Update", "Set authorized key"
- File names are kebab-case: `ssh-remove-passwd-auth.yaml`
- French comments may appear alongside English (check locale context)

## Development Workflow

### Executing Playbooks
```bash
ansible-playbook <playbook-name>.yaml -i <inventory-file>
```

### Validating Syntax
```bash
ansible-playbook --syntax-check <playbook-name>.yaml
```

### Testing Changes
- Always use `--check` mode for dry runs
- Verify idempotency: changes should not occur on second run
- Test regex patterns in `lineinfile` against target config files

## Integration Points
- **SSH Module**: Reads from local filesystem paths and modifies remote `/etc/ssh/sshd_config`
- **APT**: Requires network access and package repository connectivity
- **Handlers**: Triggered only when corresponding tasks change system state
- **Lookup Plugins**: File-based key lookups require accessible paths on control node

## When Creating New Playbooks
1. Follow the `---` header format and consistent indentation (2 spaces)
2. Include task names for CLI readability
3. Use `become: yes` for privileged operations
4. Leverage handlers for service restarts instead of inline commands
5. Apply `state: present` for idempotent changes
6. Reference existing playbooks as templates (e.g., `ssh-send-pubkey.yaml` for authorized_key patterns)

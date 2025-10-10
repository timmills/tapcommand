# TapCommand Documentation

Welcome to the TapCommand documentation! This directory contains comprehensive guides, implementation plans, and technical documentation for all aspects of the system.

## 📁 Documentation Structure

### Audio
Audio amplifier control documentation, focusing on professional audio systems via AES70/OCA protocol.

- **BOSCH_PRAESENSA_RESEARCH_FINDINGS.md** - Research on Bosch Praesensa AES70 integration
- **BOSCH_PRAESENSA_IMPLEMENTATION_PLAN.md** - Complete implementation guide for Bosch audio control
- **NETWORK_AMPLIFIER_IMPLEMENTATION_GUIDE.md** - General network amplifier integration guide

### Network-TVs
Documentation for network-based TV control, discovery, and management.

- **TV_NETWORK_CONTROL_RESEARCH.md** - Research on network TV control protocols
- **NETWORK_TV_PROOF_OF_CONCEPT.md** - Initial proof of concept for network TV control
- **NETWORK_DISCOVERY_IMPLEMENTATION.md** - TV discovery implementation via SSDP/UPnP
- **NETWORK_TV_IMPLEMENTATION_SUMMARY.md** - Summary of network TV implementation
- **NETWORK_TV_SETUP_GUIDE.md** - Setup guide for network TV controllers
- **NETWORK_TV_EXECUTORS.md** - Documentation on TV command executors
- **NETWORK_TV_STATUS_CAPABILITIES.md** - TV status polling and capabilities
- **NETWORK_DEVICE_PROTOCOLS.md** - Supported protocols (Samsung, LG, Sony, etc.)
- **SUPPORTED_NETWORK_TVS.md** - List of supported TV brands and models
- **HISENSE_IMPLEMENTATION_SUMMARY.md** - Hisense-specific implementation details
- **HYBRID_IMPLEMENTATION_GUIDE.md** - Hybrid IR/Network control guide
- **README_NETWORK_DISCOVERY.md** - Network discovery system overview

### Architecture
System architecture and design documentation.

- **NETWORK_TV_VIRTUAL_CONTROLLER_INTEGRATION.md** - Virtual Controller architecture
- **ONLINE_STATUS_MECHANISMS.md** - Online/offline status monitoring

### Device-Status
Device health monitoring and status checking documentation.

- **DEVICE_STATUS_MONITORING.md** - Device status monitoring system guide
- **DEVICE_STATUS_RESEARCH.md** - Research on device status mechanisms

### Guides
User guides and setup instructions.

- **NETWORK_ADOPTION_GUIDE.md** - Guide for adopting network devices

### User-Management
User authentication and access control documentation.

- **USER_MANAGEMENT_IMPLEMENTATION_PLAN.md** - User management system implementation

## 🚀 Quick Links

### Getting Started
- Start with **Guides/NETWORK_ADOPTION_GUIDE.md** for adopting your first network device
- See **Network-TVs/NETWORK_TV_SETUP_GUIDE.md** for TV controller setup
- Read **Audio/BOSCH_PRAESENSA_IMPLEMENTATION_PLAN.md** for audio system integration

### For Developers
- **Architecture/** - Understand system design
- **Network-TVs/NETWORK_TV_EXECUTORS.md** - Command executor pattern
- **Device-Status/** - Status monitoring implementation

### Research & Planning
- **Audio/BOSCH_PRAESENSA_RESEARCH_FINDINGS.md** - Audio protocol research
- **Network-TVs/TV_NETWORK_CONTROL_RESEARCH.md** - TV protocol research
- **Network-TVs/NETWORK_DEVICE_PROTOCOLS.md** - Protocol specifications

## 📝 Document Naming Conventions

- **RESEARCH** - Research findings and protocol analysis
- **IMPLEMENTATION** - Implementation guides and plans
- **GUIDE** - User-facing setup and usage guides
- **SUMMARY** - High-level overviews and summaries

## 🔄 Accessing Documentation

All documentation can be accessed through:
1. **Web UI**: Navigate to Documentation page in TapCommand interface
2. **File System**: Browse this directory directly
3. **API**: GET `/api/documentation/list` and `/api/documentation/content/{path}`

## 🤝 Contributing

When adding new documentation:
1. Place files in appropriate category folders
2. Use clear, descriptive filenames in UPPER_SNAKE_CASE
3. Include a header with title and brief description
4. Use markdown formatting with proper headings
5. Update this README if adding new categories

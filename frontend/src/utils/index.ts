// Utility functions

export const copyTextToClipboard = async (text: string): Promise<boolean> => {
  if (!text) {
    return false;
  }

  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (err) {
    console.error('navigator.clipboard.writeText failed:', err);
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.left = '-9999px';
  textarea.style.top = '0';
  document.body.appendChild(textarea);
  textarea.select();
  textarea.setSelectionRange(0, textarea.value.length);

  let succeeded = false;
  try {
    succeeded = document.execCommand('copy');
  } catch (err) {
    console.error('document.execCommand("copy") failed:', err);
    succeeded = false;
  }

  document.body.removeChild(textarea);
  return succeeded;
};

export const API_UNAVAILABLE_MESSAGE = 'Backend API unreachable. Ensure the SmartVenue backend service is running.';

export const getApiErrorMessage = (error: unknown, fallback: string): string => {
  if (error instanceof TypeError) {
    return API_UNAVAILABLE_MESSAGE;
  }
  if (error instanceof Error) {
    if (error.message === 'Failed to fetch') {
      return API_UNAVAILABLE_MESSAGE;
    }
    return error.message || fallback;
  }
  return fallback;
};

export const extractSubstitutionValue = (yaml: string, key: string): string => {
  const regex = new RegExp(`^\\s+${key}:\\s*(?:"([^"\\n]*)"|([^\\n#]*))`, 'm');
  const match = yaml.match(regex);
  if (!match) {
    return '';
  }
  const value = match[1] ?? match[2] ?? '';
  return value.trim();
};

export const updateYamlSubstitution = (
  yaml: string,
  key: string,
  value: string,
  wrapInQuotes = true
): string => {
  const escaped = value.replace(/"/g, '\\"');
  const regex = new RegExp(`(^\\s+${key}:\\s*)(?:"[^"\\n]*"|[^\\n]*)`, 'm');
  const replacement = wrapInQuotes ? `$1"${escaped}"` : `$1${value}`;

  if (regex.test(yaml)) {
    return yaml.replace(regex, replacement);
  }

  const substitutionsMatch = yaml.match(/^substitutions:\s*$/m);
  if (!substitutionsMatch) {
    return yaml;
  }

  const headerIndex = substitutionsMatch.index ?? 0;
  const afterHeaderIndex = yaml.indexOf('\n', headerIndex);
  const insertPosition = afterHeaderIndex >= 0 ? afterHeaderIndex + 1 : yaml.length;
  const line = wrapInQuotes
    ? `  ${key}: "${escaped}"\n`
    : `  ${key}: ${value}\n`;
  return yaml.slice(0, insertPosition) + line + yaml.slice(insertPosition);
};

export const ensureWifiHiddenBinding = (yaml: string): string => {
  const hiddenRegex = /(hidden:\s*)("?\$\{wifi_hidden\}"?|true|false|"true"|"false")/;
  const passwordRegex = /(password:\s*"?\$\{?wifi_password\}?"?.*\n)/;
  const hiddenValueRaw = extractSubstitutionValue(yaml, 'wifi_hidden');
  const normalizedHidden = hiddenValueRaw && hiddenValueRaw.toLowerCase() === 'false' ? '"false"' : '"true"';

  let updated = yaml;

  if (hiddenRegex.test(updated)) {
    updated = updated.replace(hiddenRegex, `$1${normalizedHidden}`);
  } else if (passwordRegex.test(updated)) {
    updated = updated.replace(passwordRegex, `$1      hidden: ${normalizedHidden}\n`);
  }

  return updated;
};

export const ensureProjectName = (yaml: string): string => {
  const regex = /(project:\s*\n)(\s*)name:\s*"[^"]*"/;

  if (!regex.test(yaml)) {
    return yaml;
  }

  return yaml.replace(regex, (_match, projectLine: string, indent: string) => {
    return `${projectLine}${indent}name: "smartvenue.universal_ir"`;
  });
};

export const ensureJsonInclude = (yaml: string): string => {
  if (yaml.includes('ArduinoJson.h')) {
    return yaml;
  }

  const projectBlock = /(project:\\s*\\n\\s*name:.*\\n\\s*version:.*\\n)/;
  if (projectBlock.test(yaml)) {
    return yaml.replace(projectBlock, '$1  includes:\\n    - ArduinoJson.h\\n');
  }

  const esphomeBlock = /(esphome:\\s*\\n)/;
  if (esphomeBlock.test(yaml)) {
    return yaml.replace(esphomeBlock, '$1  includes:\\n    - ArduinoJson.h\\n');
  }

  return yaml;
};

export const normalizeCapabilitiesLambda = (yaml: string): string => {
  if (!yaml.includes('DynamicJsonDocument doc(768);')) {
    return yaml;
  }

  const replacement = `      - lambda: |-\n          DynamicJsonDocument doc(768);\n          doc[\"device_id\"] = App.get_name();\n          doc[\"project\"] = \"smartvenue.universal_ir\";\n          doc[\"firmware_version\"] = \"1.0.0\";\n          auto brands = doc.createNestedArray(\"brands\");\n{{CAPABILITY_BRAND_LINES}}\n          auto commands = doc.createNestedArray(\"commands\");\n{{CAPABILITY_COMMAND_LINES}}\n          auto metadata = doc.createNestedObject(\"metadata\");\n          metadata[\"ip\"] = WiFi.localIP().toString();\n          metadata[\"mac\"] = WiFi.macAddress();\n          metadata[\"hostname\"] = App.get_name();\n          metadata[\"reported_at_ms\"] = millis();\n          std::string payload;\n          serializeJson(doc, payload);\n          id(ir_capabilities_payload).publish_state(payload);`;

  return yaml.replace(/\s+- lambda: \|-[^]*?id\(ir_capabilities_payload\)\.publish_state\(payload\);/m, replacement);
};

export const normalizeTemplateYaml = (
  yaml: string
): { yaml: string; wifiHidden: boolean; otaPassword: string } => {
  let updated = yaml;

  // Ensure wifi_hidden substitution and binding
  let hiddenValue = extractSubstitutionValue(updated, 'wifi_hidden');
  if (!hiddenValue) {
    hiddenValue = 'true';
  }
  updated = updateYamlSubstitution(updated, 'wifi_hidden', hiddenValue, false);
  updated = ensureWifiHiddenBinding(updated);
  hiddenValue = extractSubstitutionValue(updated, 'wifi_hidden') || hiddenValue;
  const hiddenBool = hiddenValue.toLowerCase() !== 'false';

  // Ensure ota_password substitution exists
  let otaValue = extractSubstitutionValue(updated, 'ota_password');
  if (!otaValue) {
    otaValue = '';
    updated = updateYamlSubstitution(updated, 'ota_password', otaValue);
  }
  otaValue = extractSubstitutionValue(updated, 'ota_password');

  updated = ensureProjectName(updated);
  updated = ensureJsonInclude(updated);
  updated = normalizeCapabilitiesLambda(updated);

  return { yaml: updated, wifiHidden: hiddenBool, otaPassword: otaValue };
};
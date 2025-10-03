#pragma once

#include <ArduinoJson.hpp>

// Restore legacy ArduinoJson v6 symbols expected by ESPHome components
using ArduinoJson::JsonArray;
using ArduinoJson::JsonDocument;
using ArduinoJson::JsonObject;
using ArduinoJson::JsonVariant;
using ArduinoJson::DeserializationError;
using ArduinoJson::DynamicJsonDocument;

import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { Card } from "../../../shared/components/Card";
import { LocationPickerStub } from "../components/LocationPickerStub";
import { useReportSubmission } from "../hooks/useReportSubmission";
import { ReportItem } from "../types";

interface ReportCreateScreenProps {
  onReportCreated?: (report: ReportItem) => void;
}

export const ReportCreateScreen: React.FC<ReportCreateScreenProps> = ({ onReportCreated }) => {
  const [description, setDescription] = useState("");
  const [addressHint, setAddressHint] = useState("Main Street, Near High School");
  const [latitude] = useState(12.9716);
  const [longitude] = useState(77.5946);

  const { loading, error, submit } = useReportSubmission();

  const handleSubmit = async (): Promise<void> => {
    if (description.trim().length < 3) {
      Alert.alert("Validation Error", "Please provide a description of at least 3 characters.");
      return;
    }

    const payload = {
      location: {
        latitude,
        longitude,
        address_hint: addressHint.trim() || undefined,
      },
      description: description.trim(),
      citizen_id: "mobile-user-anon",
      evidence: [
        {
          evidence_type: "IMAGE" as const,
          storage_uri: "mock/edge_preprocessed_001.jpg",
          mime_type: "image/jpeg",
          file_size_bytes: 154200,
        },
      ],
    };

    const created = await submit(payload);
    if (created && onReportCreated) {
      onReportCreated(created);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.header}>New Civic Report</Text>
      <Text style={styles.subHeader}>
        Report infrastructure, potholes, or drainage issues in your area.
      </Text>

      {/* Description Input */}
      <Card>
        <Text style={styles.label}>Problem Description *</Text>
        <TextInput
          style={styles.textArea}
          placeholder="Describe the defect, location details, and any safety hazards..."
          placeholderTextColor="#94A3B8"
          value={description}
          onChangeText={setDescription}
          multiline
          numberOfLines={4}
          textAlignVertical="top"
        />
      </Card>

      {/* Location (GPS Stub) */}
      <LocationPickerStub
        latitude={latitude}
        longitude={longitude}
        addressHint={addressHint}
      />

      {/* Street / Landmark Hint */}
      <Card>
        <Text style={styles.label}>Address / Landmark Hint</Text>
        <TextInput
          style={styles.input}
          placeholder="e.g. Near Bus Stop 14"
          placeholderTextColor="#94A3B8"
          value={addressHint}
          onChangeText={setAddressHint}
        />
      </Card>

      {/* Evidence Placeholder */}
      <Card style={styles.evidencePlaceholder}>
        <Text style={styles.label}>Attached Evidence</Text>
        <Text style={styles.evidenceNote}>
          Camera capture & on-device edge preprocessing pipeline: Planned for Sprint 2.
        </Text>
        <Text style={styles.evidenceMock}>
          [✓ 1 sample image reference attached for Phase 0 verification]
        </Text>
      </Card>

      {/* Error display */}
      {error ? (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      {/* Submit Button */}
      <TouchableOpacity
        style={[styles.submitButton, loading && styles.submitButtonDisabled]}
        onPress={handleSubmit}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#ffffff" />
        ) : (
          <Text style={styles.submitButtonText}>Submit Report</Text>
        )}
      </TouchableOpacity>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F1F5F9",
  },
  content: {
    padding: 16,
    paddingBottom: 40,
  },
  header: {
    fontSize: 24,
    fontWeight: "800",
    color: "#0F172A",
    marginTop: 8,
  },
  subHeader: {
    fontSize: 14,
    color: "#64748B",
    marginTop: 4,
    marginBottom: 16,
  },
  label: {
    fontSize: 13,
    fontWeight: "600",
    color: "#334155",
    marginBottom: 8,
  },
  textArea: {
    minHeight: 90,
    backgroundColor: "#F8FAFC",
    borderWidth: 1,
    borderColor: "#CBD5E1",
    borderRadius: 8,
    padding: 12,
    fontSize: 15,
    color: "#0F172A",
  },
  input: {
    height: 44,
    backgroundColor: "#F8FAFC",
    borderWidth: 1,
    borderColor: "#CBD5E1",
    borderRadius: 8,
    paddingHorizontal: 12,
    fontSize: 15,
    color: "#0F172A",
  },
  evidencePlaceholder: {
    backgroundColor: "#EFF6FF",
    borderColor: "#BFDBFE",
  },
  evidenceNote: {
    fontSize: 12,
    color: "#1E40AF",
    marginBottom: 4,
  },
  evidenceMock: {
    fontSize: 12,
    color: "#166534",
    fontWeight: "600",
  },
  errorBox: {
    backgroundColor: "#FEE2E2",
    borderRadius: 8,
    padding: 12,
    marginVertical: 8,
    borderWidth: 1,
    borderColor: "#FCA5A5",
  },
  errorText: {
    color: "#991B1B",
    fontSize: 13,
  },
  submitButton: {
    backgroundColor: "#2563EB",
    borderRadius: 10,
    height: 50,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 16,
    shadowColor: "#2563EB",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 4,
  },
  submitButtonDisabled: {
    backgroundColor: "#93C5FD",
  },
  submitButtonText: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "700",
  },
});

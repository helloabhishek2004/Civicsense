import React from "react";
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Card } from "../../../shared/components/Card";
import { StatusBadge } from "../components/StatusBadge";
import { ReportItem } from "../types";

interface ReportDetailScreenProps {
  report: ReportItem;
  onBack: () => void;
}

export const ReportDetailScreen: React.FC<ReportDetailScreenProps> = ({ report, onBack }) => {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <TouchableOpacity style={styles.backButton} onPress={onBack}>
        <Text style={styles.backButtonText}>← Back to Report Submission</Text>
      </TouchableOpacity>

      <View style={styles.headerRow}>
        <View>
          <Text style={styles.trackingLabel}>Tracking ID</Text>
          <Text style={styles.trackingId}>{report.tracking_id}</Text>
        </View>
        <StatusBadge status={report.status} />
      </View>

      <Card>
        <Text style={styles.sectionTitle}>Problem Description</Text>
        <Text style={styles.descriptionText}>{report.description}</Text>
      </Card>

      <Card>
        <Text style={styles.sectionTitle}>Observed Location</Text>
        <Text style={styles.locationText}>
          {report.latitude.toFixed(6)}, {report.longitude.toFixed(6)}
        </Text>
        {report.address_hint ? (
          <Text style={styles.addressText}>{report.address_hint}</Text>
        ) : null}
      </Card>

      <Card>
        <Text style={styles.sectionTitle}>Attached Evidence</Text>
        <Text style={styles.evidenceInfo}>
          {report.evidences?.length || 0} evidence asset(s) linked to report record.
        </Text>
      </Card>

      <Card>
        <Text style={styles.sectionTitle}>Lifecycle Timeline</Text>
        <Text style={styles.timelineItem}>
          • Submitted at: {new Date(report.created_at).toLocaleString()}
        </Text>
        <Text style={styles.timelineSubText}>
          Next automated step: Server AI Ingestion & Analysis (Planned for Sprint 3-5).
        </Text>
      </Card>
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
  backButton: {
    paddingVertical: 8,
    marginBottom: 8,
  },
  backButtonText: {
    color: "#2563EB",
    fontSize: 14,
    fontWeight: "600",
  },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginVertical: 12,
  },
  trackingLabel: {
    fontSize: 12,
    color: "#64748B",
    textTransform: "uppercase",
    fontWeight: "600",
  },
  trackingId: {
    fontSize: 20,
    fontWeight: "800",
    color: "#0F172A",
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: "700",
    color: "#475569",
    marginBottom: 6,
    textTransform: "uppercase",
  },
  descriptionText: {
    fontSize: 15,
    color: "#1E293B",
    lineHeight: 22,
  },
  locationText: {
    fontSize: 15,
    fontWeight: "600",
    color: "#0F172A",
  },
  addressText: {
    fontSize: 13,
    color: "#64748B",
    marginTop: 2,
  },
  evidenceInfo: {
    fontSize: 14,
    color: "#334155",
  },
  timelineItem: {
    fontSize: 14,
    color: "#0F172A",
    fontWeight: "600",
  },
  timelineSubText: {
    fontSize: 12,
    color: "#64748B",
    marginTop: 4,
    fontStyle: "italic",
  },
});

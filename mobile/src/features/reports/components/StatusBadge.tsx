import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { ReportStatus } from "../../../shared/types/common";

interface StatusBadgeProps {
  status: ReportStatus;
}

const STATUS_COLORS: Record<ReportStatus, { bg: string; text: string }> = {
  SUBMITTED: { bg: "#E0F2FE", text: "#0369A1" },
  AI_PROCESSING: { bg: "#FEF3C7", text: "#B45309" },
  AI_PROCESSED: { bg: "#EDE9FE", text: "#6D28D9" },
  VERIFICATION_REQUIRED: { bg: "#FEE2E2", text: "#B91C1C" },
  VERIFIED: { bg: "#DCFCE7", text: "#15803D" },
  PRIORITIZED: { bg: "#FFEDD5", text: "#C2410C" },
  ASSIGNED: { bg: "#E0E7FF", text: "#4338CA" },
  IN_PROGRESS: { bg: "#DBEAFE", text: "#1D4ED8" },
  RESOLVED: { bg: "#D1FAE5", text: "#047857" },
  RESOLUTION_VERIFIED: { bg: "#CCFBF1", text: "#0F766E" },
  CLOSED: { bg: "#F3F4F6", text: "#4B5563" },
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const color = STATUS_COLORS[status] || { bg: "#F3F4F6", text: "#4B5563" };

  return (
    <View style={[styles.badge, { backgroundColor: color.bg }]}>
      <Text style={[styles.text, { color: color.text }]}>{status.replace(/_/g, " ")}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 16,
    alignSelf: "flex-start",
  },
  text: {
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 0.5,
  },
});

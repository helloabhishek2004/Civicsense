import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { Card } from "../../../shared/components/Card";

interface LocationPickerStubProps {
  latitude: number;
  longitude: number;
  addressHint?: string;
}

export const LocationPickerStub: React.FC<LocationPickerStubProps> = ({
  latitude,
  longitude,
  addressHint,
}) => {
  return (
    <Card style={styles.container}>
      <Text style={styles.title}>Location (Simulated Edge GPS)</Text>
      <Text style={styles.coords}>
        {latitude.toFixed(6)}, {longitude.toFixed(6)}
      </Text>
      {addressHint ? <Text style={styles.hint}>{addressHint}</Text> : null}
      <Text style={styles.note}>GPS coordinates attached automatically</Text>
    </Card>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#F8FAFC",
    borderColor: "#E2E8F0",
  },
  title: {
    fontSize: 13,
    fontWeight: "600",
    color: "#64748B",
    marginBottom: 4,
    textTransform: "uppercase",
  },
  coords: {
    fontSize: 16,
    fontWeight: "700",
    color: "#0F172A",
  },
  hint: {
    fontSize: 13,
    color: "#334155",
    marginTop: 2,
  },
  note: {
    fontSize: 11,
    color: "#94A3B8",
    marginTop: 6,
    fontStyle: "italic",
  },
});

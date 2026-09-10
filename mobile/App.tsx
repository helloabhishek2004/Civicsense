import { StatusBar } from "expo-status-bar";
import React, { useState } from "react";
import { SafeAreaView, StyleSheet, View } from "react-native";
import { ReportCreateScreen } from "./src/features/reports/screens/ReportCreateScreen";
import { ReportDetailScreen } from "./src/features/reports/screens/ReportDetailScreen";
import { ReportItem } from "./src/features/reports/types";

export default function App(): React.JSX.Element {
  const [currentScreen, setCurrentScreen] = useState<"CREATE" | "DETAIL">("CREATE");
  const [activeReport, setActiveReport] = useState<ReportItem | null>(null);

  const handleReportCreated = (report: ReportItem): void => {
    setActiveReport(report);
    setCurrentScreen("DETAIL");
  };

  const handleBackToCreate = (): void => {
    setActiveReport(null);
    setCurrentScreen("CREATE");
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="dark" />
      <View style={styles.container}>
        {currentScreen === "CREATE" || !activeReport ? (
          <ReportCreateScreen onReportCreated={handleReportCreated} />
        ) : (
          <ReportDetailScreen report={activeReport} onBack={handleBackToCreate} />
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#F1F5F9",
  },
  container: {
    flex: 1,
  },
});

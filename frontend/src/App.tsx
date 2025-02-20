import React from 'react';
import { ChakraProvider, Box, Grid } from '@chakra-ui/react';
import { Dashboard } from './components/Dashboard';
import { MetricsPanel } from './components/MetricsPanel';
import { PerformanceChart } from './components/PerformanceChart';

export const App = () => {
  return (
    <ChakraProvider>
      <Box p={5}>
        <Grid templateColumns="repeat(3, 1fr)" gap={6}>
          <Dashboard />
          <MetricsPanel />
          <PerformanceChart />
        </Grid>
      </Box>
    </ChakraProvider>
  );
};




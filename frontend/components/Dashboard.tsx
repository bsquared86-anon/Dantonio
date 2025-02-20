import React, { useState, useEffect } from 'react';
import { Box, Stat, StatLabel, StatNumber, StatGroup } from '@chakra-ui/react';
import { useWebSocket } from '../hooks/useWebSocket';

export const Dashboard = () => {
  const { metrics } = useWebSocket('ws://localhost:8000/ws');

  return (
    <Box p={5} shadow="xl" borderRadius="lg">
      <StatGroup>
        <Stat>
          <StatLabel>Gas Price</StatLabel>
          <StatNumber>{metrics.gas_price} Gwei</StatNumber>
        </Stat>
        <Stat>
          <StatLabel>Total Profit</StatLabel>
          <StatNumber>{metrics.profit} ETH</StatNumber>
        </Stat>
        <Stat>
          <StatLabel>Active Strategies</StatLabel>
          <StatNumber>{metrics.active_strategies}</StatNumber>
        </Stat>
      </StatGroup>
    </Box>
  );
};


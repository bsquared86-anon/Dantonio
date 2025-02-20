import React from 'react';
import { Box, Grid, Typography, Chip, Tooltip } from '@mui/material';
import { styled } from '@mui/material/styles';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import LocalGasStationIcon from '@mui/icons-material/LocalGasStation';
import WarningIcon from '@mui/icons-material/Warning';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

const MetricBox = styled(Box)(({ theme }) => ({
  padding: theme.spacing(2),
  borderRadius: theme.shape.borderRadius,
  backgroundColor: theme.palette.background.paper,
  boxShadow: theme.shadows[1],
  transition: 'all 0.3s ease',
  '&:hover': {
    boxShadow: theme.shadows[3],
    transform: 'translateY(-2px)',
  },
}));

interface MetricsPanelProps {
  metrics: {
    profit: number;
    gasPrice: number;
    slippage: number;
    executedStrategies: number;
    successRate: number;
    activeStrategies: number;
  };
  riskMetrics: {
    riskLevel: string;
    exposureLevel: number;
    warningCount: number;
  };
}

const MetricsPanel: React.FC<MetricsPanelProps> = ({ metrics, riskMetrics }) => {
  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const getRiskLevelColor = (level: string): string => {
    switch (level.toUpperCase()) {
      case 'HIGH':
        return '#f44336';
      case 'MEDIUM':
        return '#ff9800';
      case 'LOW':
        return '#4caf50';
      default:
        return '#757575';
    }
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Performance Metrics
      </Typography>
      
      <Grid container spacing={2}>
        {/* Profit Metric */}
        <Grid item xs={12}>
          <MetricBox>
            <Typography variant="subtitle2" color="textSecondary">
              Total Profit
            </Typography>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Typography variant="h4">
                {formatCurrency(metrics.profit)}
              </Typography>
              <TrendingUpIcon color="primary" />
            </Box>
          </MetricBox>
        </Grid>

        {/* Gas Price Metric */}
        <Grid item xs={6}>
          <MetricBox>
            <Typography variant="subtitle2" color="textSecondary">
              Gas Price
            </Typography>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Typography variant="h6">
                {metrics.gasPrice} GWEI
              </Typography>
              <LocalGasStationIcon color="secondary" />
            </Box>
          </MetricBox>
        </Grid>

        {/* Success Rate Metric */}
        <Grid item xs={6}>
          <MetricBox>
            <Typography variant="subtitle2" color="textSecondary">
              Success Rate
            </Typography>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Typography variant="h6">
                {metrics.successRate}%
              </Typography>
              <CheckCircleIcon color="success" />
            </Box>
          </MetricBox>
        </Grid>

        {/* Risk Level */}
        <Grid item xs={12}>
          <MetricBox>
            <Typography variant="subtitle2" color="textSecondary">
              Risk Level
            </Typography>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Chip
                label={riskMetrics.riskLevel}
                style={{ backgroundColor: getRiskLevelColor(riskMetrics.riskLevel) }}
              />
              <Tooltip title={`${riskMetrics.warningCount} active warnings`}>
                <Box display="flex" alignItems="center">
                  <WarningIcon color="warning" />
                  <Typography variant="body2" ml={1}>
                    {riskMetrics.warningCount}
                  </Typography>
                </Box>
              </Tooltip>
            </Box>
          </MetricBox>
        </Grid>

        {/* Strategy Stats */}
        <Grid item xs={12}>
          <MetricBox>
            <Typography variant="subtitle2" color="textSecondary">
              Strategy Overview
            </Typography>
            <Box display="flex" justifyContent="space-between" mt={1}>
              <Typography variant="body2">
                Active: {metrics.activeStrategies}
              </Typography>
              <Typography variant="body2">
                Executed: {metrics.executedStrategies}
              </Typography>
            </Box>
          </MetricBox>
        </Grid>
      </Grid>
    </Box>
  );
};

export default MetricsPanel;


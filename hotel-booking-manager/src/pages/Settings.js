import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  InputAdornment,
  CircularProgress,
  FormHelperText,
  Tooltip,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import AddIcon from '@mui/icons-material/Add';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import { settingsApi } from '../services/api';

const Settings = ({ showSnackbar }) => {
  const [emailConfigs, setEmailConfigs] = useState([]);
  const [jobStatuses, setJobStatuses] = useState([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingConfig, setEditingConfig] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const [visiblePasswords, setVisiblePasswords] = useState({});
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    fetchInterval: 15,
  });
  const [runningConfigs, setRunningConfigs] = useState(new Set());
  const [globalSettings, setGlobalSettings] = useState({
    googleSheetUrl: '',
    sheetName: ''
  });
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const fetchConfigs = useCallback(async () => {
    try {
      setLoading(true);
      const [configs, statuses, settings] = await Promise.all([
        settingsApi.getAllConfigs(),
        settingsApi.getJobStatuses(),
        settingsApi.getGlobalSettings()
      ]);
      console.log(configs);
      
      setEmailConfigs(configs);
      setJobStatuses(statuses || []);
      setGlobalSettings(settings || { googleSheetUrl: '', sheetName: '' });
    } catch (error) {
      console.error(error)
      showSnackbar('Error fetching configurations', 'error');
    } finally {
      setLoading(false);
    }
  }, [showSnackbar]);

  useEffect(() => {
    fetchConfigs();
  }, [fetchConfigs]);

  const handleOpenDialog = (config = null) => {
    if (config) {
      setEditingConfig(config);
      setFormData({
        email: config.email,
        password: '', // Don't show the actual password
        fetchInterval: config.fetchInterval,
      });
    } else {
      setEditingConfig(null);
      setFormData({
        email: '',
        password: '',
        fetchInterval: 15,
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingConfig(null);
    setShowPassword(false);
    setFormData({
      email: '',
      password: '',
      fetchInterval: 15,
    });
  };

  const validateForm = () => {
    if (!formData.email) {
      showSnackbar('Email is required', 'error');
      return false;
    }
    if (!formData.password) {
      showSnackbar('Password is required', 'error');
      return false;
    }
    if (!formData.fetchInterval) {
      showSnackbar('Fetch interval is required', 'error');
      return false;
    }

    return true;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    try {
      setLoading(true);
      const configData = {
        email: formData.email,
        password: formData.password,
        fetchInterval: Number(formData.fetchInterval),
      };

      if (editingConfig) {
        // Update existing config
        const updatedConfig = await settingsApi.updateConfig(editingConfig.id, configData);
        setEmailConfigs(emailConfigs.map(config =>
          config.id === editingConfig.id ? updatedConfig : config
        ));
        showSnackbar('Email configuration updated successfully', 'success');
      } else {
        // Add new config
        const newConfig = await settingsApi.createConfig(configData);
        setEmailConfigs([...emailConfigs, newConfig]);
        showSnackbar('Email configuration added successfully', 'success');
      }
      handleCloseDialog();
    } catch (error) {
      console.error('Error saving configuration:', error);
      showSnackbar(error.message || 'Error saving configuration', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      setLoading(true);
      await settingsApi.deleteConfig(id);
      setEmailConfigs(emailConfigs.filter(config => config.id !== id));
      showSnackbar('Email configuration deleted successfully', 'success');
    } catch (error) {
      showSnackbar(error.message || 'Error deleting configuration', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleClickShowPassword = () => {
    setShowPassword(!showPassword);
  };

  const togglePasswordVisibility = (id) => {
    setVisiblePasswords(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  const handleRunNow = async (id) => {
    try {
      setLoading(true);
      setRunningConfigs(prev => new Set([...prev, id]));
      await settingsApi.runEmailFetch(id);
      showSnackbar('Email configuration run now initiated', 'success');
    } catch (error) {
      console.error('Error running email configuration:', error);
      showSnackbar(error.message || 'Error running email configuration', 'error');
    } finally {
      setLoading(false);
      setRunningConfigs(prev => {
        const newSet = new Set(prev);
        newSet.delete(id);
        return newSet;
      });
    }
  };

  const handleGlobalSettingsChange = (newUrl) => {
    setGlobalSettings({ ...globalSettings, googleSheetUrl: newUrl });
  };
  const handleSheetNameSettingsChange = (newUrl) => {
    setGlobalSettings({ ...globalSettings, sheetName: newUrl });
  };

  const handleSaveGlobalSettings = async () => {
    try {
      setIsSavingSettings(true);
      await settingsApi.updateGlobalSettings({ googleSheetUrl: globalSettings.googleSheetUrl, sheetName: globalSettings.sheetName });
      showSnackbar('Global settings saved successfully', 'success');
    } catch (error) {
      showSnackbar(error.message || 'Error saving global settings', 'error');
    } finally {
      setIsSavingSettings(false);
    }
  };

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h5" sx={{ mb: 2 }}>Global Settings</Typography>
        <Paper sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
            <TextField
              label="Google Sheet URL"
              type="url"
              fullWidth
              value={globalSettings.googleSheetUrl}
              onChange={(e) => handleGlobalSettingsChange(e.target.value)}
              disabled={isSavingSettings}
              error={globalSettings.googleSheetUrl.trim().length === 0}
              helperText={
                globalSettings.googleSheetUrl.trim().length === 0
                  ? 'Invalid Google Sheet URL format'
                  : 'Enter the Google Sheet URL where booking data will be saved'
              }
            />
            <TextField
              label="Sheet Name"
              type="text"
              fullWidth
              value={globalSettings.sheetName}
              onChange={(e) => handleSheetNameSettingsChange(e.target.value)}
              disabled={isSavingSettings}
              error={globalSettings.sheetName.trim().length === 0}
              helperText={
                globalSettings.sheetName.trim().length === 0
                  ? 'Invalid Google Sheet URL format'
                  : 'Enter the Google Sheet URL where booking data will be saved'
              }
            />
            <Button
              variant="contained"
              onClick={handleSaveGlobalSettings}
              disabled={isSavingSettings || !globalSettings.googleSheetUrl}
              sx={{ minWidth: '100px' }}
            >
              {isSavingSettings ? <CircularProgress size={24} /> : 'Save'}
            </Button>
          </Box>
        </Paper>
      </Box>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5">Email Fetching Settings</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenDialog()}
          disabled={loading}
        >
          Add Email Configuration
        </Button>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Email Address</TableCell>
                <TableCell>Password</TableCell>
                <TableCell>Fetch Interval (minutes)</TableCell>
                <TableCell>Next Run</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {emailConfigs.map((config) => {
                const status = Array.isArray(jobStatuses) ? 
                  jobStatuses.find(s => s.id === config.id) : null;
                const isRunning = runningConfigs.has(config.id);
                return (
                  <TableRow key={config.id}>
                    <TableCell>{config.email}</TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {visiblePasswords[config.id] ? config.password : '••••••••'}
                        <IconButton
                          size="small"
                          onClick={() => togglePasswordVisibility(config.id)}
                          edge="end"
                        >
                          {visiblePasswords[config.id] ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      </Box>
                    </TableCell>
                    <TableCell>{config.fetchInterval}</TableCell>
                    <TableCell>
                      {status?.next_run ? (
                        <Typography variant="body2">
                          {new Date(status.next_run.next_run).toLocaleString()}
                          <br />
                          <Typography variant="caption" color="textSecondary">
                            {status.next_run.time_until} until next run
                          </Typography>
                        </Typography>
                      ) : (
                        <Typography variant="body2" color="textSecondary">
                          Not scheduled
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title="Run Now">
                        <IconButton
                          onClick={() => handleRunNow(config.id)}
                          disabled={loading || isRunning}
                          color="primary"
                        >
                          {isRunning ? <CircularProgress size={24} /> : <PlayArrowIcon />}
                        </IconButton>
                      </Tooltip>
                      <IconButton 
                        onClick={() => handleOpenDialog(config)}
                        disabled={loading}
                      >
                        <EditIcon />
                      </IconButton>
                      <IconButton 
                        onClick={() => handleDelete(config.id)}
                        disabled={loading}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog open={openDialog} onClose={handleCloseDialog}>
        <DialogTitle>
          {editingConfig ? 'Edit Email Configuration' : 'Add Email Configuration'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Email Address"
              type="email"
              fullWidth
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              disabled={loading}
              error={!formData.email}
              helperText={!formData.email ? 'Email is required' : ''}
            />
            <TextField
              label="Password"
              type={showPassword ? 'text' : 'password'}
              fullWidth
              required
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              disabled={loading}
              error={!formData.password}
              helperText={!formData.password ? 'Password is required' : ''}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label="toggle password visibility"
                      onClick={handleClickShowPassword}
                      edge="end"
                    >
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            <FormControl fullWidth required error={!formData.fetchInterval}>
              <InputLabel>Fetch Interval</InputLabel>
              <Select
                value={formData.fetchInterval}
                label="Fetch Interval"
                onChange={(e) => setFormData({ ...formData, fetchInterval: Number(e.target.value) })}
                disabled={loading}
              >
                <MenuItem value={5}>5 minutes</MenuItem>
                <MenuItem value={15}>15 minutes</MenuItem>
                <MenuItem value={30}>30 minutes</MenuItem>
                <MenuItem value={60}>1 hour</MenuItem>
              </Select>
              {!formData.fetchInterval && (
                <FormHelperText>Fetch interval is required</FormHelperText>
              )}
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog} disabled={loading}>Cancel</Button>
          <Button 
            onClick={handleSubmit} 
            variant="contained"
            disabled={loading || !formData.email || !formData.password || !formData.fetchInterval}
          >
            {loading ? <CircularProgress size={24} /> : (editingConfig ? 'Update' : 'Add')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Settings; 
import React, { useState } from 'react';
import { AppBar, Toolbar, Typography, Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText, Box, CssBaseline, ThemeProvider, createTheme, Snackbar, Alert } from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import EmailIcon from '@mui/icons-material/Email';
import Settings from './pages/Settings';
import EmailList from './pages/EmailList';
import ExcelImport from './pages/ExcelImport';
import { Routes, Route, BrowserRouter, useNavigate } from 'react-router-dom';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';

const drawerWidth = 240;

const theme = createTheme({
  palette: {
    primary: {
      main: '#607d8b', // Blue Grey
    },
    secondary: {
      main: '#ff9800', // Orange
    },
  },
  spacing: 8, // Default spacing unit
});

function AppContent() {
  const [selectedPage, setSelectedPage] = useState('Settings');
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState('success');
  const navigate = useNavigate();

  const handleDrawerToggle = (page) => {
    setSelectedPage(page);
    // Navigate to the corresponding route
    const route = menuItems.find(item => item.text === page)?.path || '/';
    navigate(route);
  };

  const showSnackbar = (message, severity) => {
    setSnackbarMessage(message);
    setSnackbarSeverity(severity);
    setSnackbarOpen(true);
  };

  const handleCloseSnackbar = (event, reason) => {
    if (reason === 'clickaway') {
      return;
    }
    setSnackbarOpen(false);
  };

  const menuItems = [
    { text: 'Email List', icon: <EmailIcon />, path: '/emails' },
    { text: 'Settings', icon: <SettingsIcon />, path: '/' },
    { text: 'Excel Import', icon: <CloudUploadIcon />, path: '/excel-import' },
  ];

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography variant="h6" noWrap component="div">
            Hotel Booking Manager
          </Typography>
        </Toolbar>
      </AppBar>
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': { width: drawerWidth, boxSizing: 'border-box' },
        }}
      >
        <Toolbar />
        <Box sx={{ overflow: 'auto' }}>
          <List>
            {menuItems.map((item) => (
              <ListItem key={item.text} disablePadding>
                <ListItemButton onClick={() => handleDrawerToggle(item.text)}>
                  <ListItemIcon>
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText primary={item.text} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        </Box>
      </Drawer>
      <Box
        component="main"
        sx={{ flexGrow: 1, p: 3, width: { sm: `calc(100% - ${drawerWidth}px)` } }}
      >
        <Toolbar />
        <Routes>
          <Route path="/" element={<Settings showSnackbar={showSnackbar} />} />
          <Route path="/emails" element={<EmailList showSnackbar={showSnackbar} />} />
          <Route path="/excel-import" element={<ExcelImport showSnackbar={showSnackbar} />} />
        </Routes>
      </Box>
      <Snackbar open={snackbarOpen} autoHideDuration={6000} onClose={handleCloseSnackbar}>
        <Alert onClose={handleCloseSnackbar} severity={snackbarSeverity} sx={{ width: '100%' }}>
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
}

function App() {
  return (
    <ThemeProvider theme={theme}>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;

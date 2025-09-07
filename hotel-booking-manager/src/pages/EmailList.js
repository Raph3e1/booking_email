import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  IconButton,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import { emailApi } from '../services/api';

function EmailList({ showSnackbar }) {
  const [emails, setEmails] = useState([]);
  const [open, setOpen] = useState(false);
  const [editingEmail, setEditingEmail] = useState(null);
  const [emailAddress, setEmailAddress] = useState('');

  useEffect(() => {
    fetchEmails();
  }, []);

  const fetchEmails = async () => {
    try {
      const data = await emailApi.getAll();
      setEmails(data);
    } catch (error) {
      showSnackbar('Failed to fetch emails', 'error');
    }
  };

  const handleOpen = (email = null) => {
    if (email) {
      setEditingEmail(email);
      setEmailAddress(email.email);
    } else {
      setEditingEmail(null);
      setEmailAddress('');
    }
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
    setEditingEmail(null);
    setEmailAddress('');
  };

  const handleSubmit = async () => {
    try {
      if (editingEmail) {
        await emailApi.update(editingEmail.id, emailAddress);
        showSnackbar('Email updated successfully', 'success');
      } else {
        await emailApi.add(emailAddress);
        showSnackbar('Email added successfully', 'success');
      }
      handleClose();
      fetchEmails();
    } catch (error) {
      showSnackbar('Failed to save email', 'error');
    }
  };

  const handleDelete = async (id) => {
    try {
      await emailApi.delete(id);
      showSnackbar('Email deleted successfully', 'success');
      fetchEmails();
    } catch (error) {
      showSnackbar('Failed to delete email', 'error');
    }
  };

  return (
    <Box>
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'flex-end' }}>
        <Button variant="contained" onClick={() => handleOpen()}>
          Add New Email
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Email</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {emails.map((email) => (
              <TableRow key={email.id}>
                <TableCell>{email.email}</TableCell>
                <TableCell>
                  <IconButton onClick={() => handleOpen(email)}>
                    <EditIcon />
                  </IconButton>
                  <IconButton onClick={() => handleDelete(email.id)}>
                    <DeleteIcon />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={open} onClose={handleClose}>
        <DialogTitle>
          {editingEmail ? 'Edit Email' : 'Add New Email'}
        </DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Email"
            type="email"
            fullWidth
            value={emailAddress}
            onChange={(e) => setEmailAddress(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Cancel</Button>
          <Button onClick={handleSubmit} variant="contained">
            {editingEmail ? 'Update' : 'Add'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default EmailList; 
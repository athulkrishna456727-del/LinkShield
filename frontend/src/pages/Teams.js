import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/Layout';
import { Users, UserPlus, Trash2, Crown, Shield } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

const Teams = () => {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const [team, setTeam] = useState(null);
  const [loading, setLoading] = useState(true);
  const [teamName, setTeamName] = useState('');
  const [memberEmail, setMemberEmail] = useState('');
  const [memberRole, setMemberRole] = useState('member');
  const [addingMember, setAddingMember] = useState(false);

  useEffect(() => {
    if (user?.plan !== 'enterprise') {
      navigate('/plans');
      return;
    }
    fetchTeam();
  }, [user]);

  const fetchTeam = async () => {
    try {
      const res = await axios.get(`${API_URL}/teams/my`, { headers: { Authorization: `Bearer ${token}` } });
      setTeam(res.data);
    } catch (error) {
      if (error.response?.status === 403) navigate('/plans');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTeam = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_URL}/teams`, { name: teamName }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Team created!');
      setTeamName('');
      fetchTeam();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create team');
    }
  };

  const handleAddMember = async (e) => {
    e.preventDefault();
    setAddingMember(true);
    try {
      await axios.post(`${API_URL}/teams/members`, { email: memberEmail, role: memberRole }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Member added!');
      setMemberEmail('');
      fetchTeam();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add member');
    } finally {
      setAddingMember(false);
    }
  };

  const handleRemoveMember = async (memberId) => {
    if (!window.confirm('Remove this member from the team?')) return;
    try {
      await axios.delete(`${API_URL}/teams/members/${memberId}`, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Member removed');
      fetchTeam();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to remove member');
    }
  };

  if (user?.plan !== 'enterprise') return null;
  if (loading) return <Layout><div className="flex items-center justify-center py-20"><p className="text-muted-foreground">Loading...</p></div></Layout>;

  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="teams-page">
        <div className="mb-8">
          <h1 className="font-heading text-4xl font-bold mb-2 flex items-center">
            <Users className="h-10 w-10 text-primary mr-3" />
            Team Workspace
          </h1>
          <p className="text-muted-foreground">Manage your security operations team</p>
        </div>

        {!team?.has_team ? (
          <div className="bg-card border border-border rounded-xl p-8 text-center">
            <Users className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
            <h2 className="font-heading text-2xl font-semibold mb-2">Create Your Team</h2>
            <p className="text-muted-foreground mb-6">Set up a workspace for your security team (up to 50 members)</p>
            <form onSubmit={handleCreateTeam} className="max-w-sm mx-auto space-y-4">
              <Input
                placeholder="Team name"
                value={teamName}
                onChange={(e) => setTeamName(e.target.value)}
                required
                data-testid="team-name-input"
              />
              <Button type="submit" className="w-full" data-testid="create-team-btn">
                <Crown className="h-4 w-4 mr-2" /> Create Team
              </Button>
            </form>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="bg-card border border-border rounded-xl p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="font-heading text-2xl font-semibold">{team.name}</h2>
                  <p className="text-sm text-muted-foreground">{team.members?.length || 0} members</p>
                </div>
                <span className="px-3 py-1 bg-purple-500/10 text-purple-400 text-xs font-mono rounded-full border border-purple-500/20">ENTERPRISE</span>
              </div>

              <div className="space-y-3">
                {team.members?.map((member) => (
                  <div key={member.id} className="flex items-center justify-between p-4 bg-accent/30 rounded-lg border border-border/50">
                    <div className="flex items-center space-x-3">
                      <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                        {member.role === 'owner' ? <Crown className="h-5 w-5 text-primary" /> : <Shield className="h-5 w-5 text-muted-foreground" />}
                      </div>
                      <div>
                        <p className="font-semibold">{member.user_info?.name || 'Unknown'}</p>
                        <p className="text-sm text-muted-foreground">{member.user_info?.email}</p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <span className="text-xs font-mono uppercase px-2 py-1 bg-accent rounded">{member.role}</span>
                      {member.role !== 'owner' && member.user_id !== user.id && (
                        <Button variant="ghost" size="sm" onClick={() => handleRemoveMember(member.user_id)} data-testid={`remove-member-${member.user_id}`}>
                          <Trash2 className="h-4 w-4 text-red-400" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-card border border-border rounded-xl p-6">
              <h3 className="font-heading text-xl font-semibold mb-4 flex items-center">
                <UserPlus className="h-5 w-5 text-primary mr-2" /> Add Member
              </h3>
              <form onSubmit={handleAddMember} className="flex items-end gap-3" data-testid="add-member-form">
                <div className="flex-1">
                  <Label>Email</Label>
                  <Input
                    type="email"
                    placeholder="user@example.com"
                    value={memberEmail}
                    onChange={(e) => setMemberEmail(e.target.value)}
                    required
                    className="mt-1"
                    data-testid="member-email-input"
                  />
                </div>
                <div className="w-36">
                  <Label>Role</Label>
                  <Select value={memberRole} onValueChange={setMemberRole}>
                    <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="member">Member</SelectItem>
                      <SelectItem value="admin">Admin</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button type="submit" disabled={addingMember} data-testid="add-member-btn">
                  {addingMember ? 'Adding...' : 'Add'}
                </Button>
              </form>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default Teams;

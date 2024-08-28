from django.urls import path , re_path

from ..views.challenge import challenge
app_name = 'challenge'
urlpatterns = [
    #---------------------------------------------------------------------
    path('challenge/list/',challenge.ChallengeList,name='challenge_list'),
    path('cahllenge/add/',challenge.AddChallenge,name='add_challenge'),
    path('cahllenge/add_solution/',challenge.AddSolution,name='add_solution'),
    path('challenge/challenge_detail/<int:challenge_id>/',challenge.ChallengeDetail,name='challenge_detail'),
    path('challenge/same_challenge/<int:challenge_id>/',challenge.HaveSameChallenge,name='same_challenge'),
    path('challenge/add_challenge_comment/<int:challenge_id>/',challenge.AddChallengeComment,name='add_challenge_comment'),
    path('challenge/add_solution_comment/<int:solution_id>/',challenge.AddSolutionComment,name='add_solution_comment'),
    path('challenge/solution_votes/<int:solution_id>/<int:vote_value>/',challenge.GetSolutionVotes,name='solution_votes'),
    path('challenge/confirm_solution/<int:solution_id>/',challenge.ConfirmSolution,name='confirm_solution'),
    path('challenge/unconfirm_solution/<int:solution_id>/',challenge.UnConfirmSolution,name='unconfirm_solution'),
]
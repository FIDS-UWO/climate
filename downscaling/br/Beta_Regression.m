function [Simulated_Precipitation] = Beta_Regression(x,y,z)
% THIS CODE IS FOR CART AND PCA
%x=Training period Predictor Variables e.g. tasmax, tasmin,psl,mslp,ua,va
%y=Training period Predictand Variable e.g. Precipitation
%z=Testing period Predictor Variables (data points where regression value
%will be calculated)  
% Length of Tranning predictor data and predictand should be same
if length(x)~=length(y);
    disp('Input Matrix length should be same for Predictor and Predictand ')
end

% Matrix dimension should be same for training period and testing period predictors
if size(x,2)~=size(z,2)
    disp('Training and Testing period predictors dimension is not same')
end

Traning_Predictor=x(:,4:end);
Tranning_Predictand=y(:,4:end);
Testing_Predictor=z(:,4:end);  
Testing_Predictor_Date=z(:,1:3);
% Kmeans clustering for rainfall state
rand('state',0);
% Three clusters has taken for clustering, do cluster validation before
% choose the no of clusters
k=3;
[IDX,C,sumd,D]= kmeans(Tranning_Predictand,k); % IDX is the rainfall state for observed data

% Normaization of the Predictor variable (1960-1990)
[Z,mu,sigma] = zscore(Traning_Predictor);
%PCA 
[pc,score1,latent1] = princomp(Z);
Var=(cumsum((latent1)./sum(latent1))*100);
% Find the variance which is less or equal to 98%
Ln_var_explained=length(find(Var<=98));
%Buliding classification Tree
T=classregtree(score1(2:end,1:Ln_var_explained),IDX(1:end-1,:));
%sub_mean_data=bsxfun(@minus, Testing_Predictor, mu); % substraction from mean
%Testing_Predictor=bsxfun(@rdivide,sub_mean_data,sigma);% %Standarization future predictor data
Temp_val=zscore(Testing_Predictor)*pc;
Rain_state_Prediction_Traning_Period=T(Temp_val(:,1:Ln_var_explained));

% Vector Space of observed data pr on the basis of rainfall state tranning
% period
Observed_data_pr_Rainfall_state=[Tranning_Predictand IDX];
observed_pr_data_state_1=(Observed_data_pr_Rainfall_state(Observed_data_pr_Rainfall_state(:,end)==1, 1:end-1));
% Scaling the data in range (0,1)
Pr_tranning_1=bsxfun(@times,(bsxfun(@minus, observed_pr_data_state_1, min(observed_pr_data_state_1))), (1./(max(observed_pr_data_state_1)-min(observed_pr_data_state_1))));
Tranning_Predictand_state1=((Pr_tranning_1*(length(Pr_tranning_1)-1))+0.5)/length(Pr_tranning_1);
observed_pr_data_state_2=(Observed_data_pr_Rainfall_state(Observed_data_pr_Rainfall_state(:,end)==2, 1:end-1));
% Scaling the data in range (0,1)
Pr_tranning_2=bsxfun(@times,(bsxfun(@minus, observed_pr_data_state_2, min(observed_pr_data_state_2))), (1./(max(observed_pr_data_state_2)-min(observed_pr_data_state_2))));
Tranning_Predictand_state2=((Pr_tranning_2*(length(Pr_tranning_2)-1))+0.5)/length(Pr_tranning_2);

observed_pr_data_state_3=(Observed_data_pr_Rainfall_state(Observed_data_pr_Rainfall_state(:,end)==3, 1:end-1));
% Scaling the data in range (0,1)
Pr_tranning_3=bsxfun(@times,(bsxfun(@minus, observed_pr_data_state_3, min(observed_pr_data_state_3))), (1./(max(observed_pr_data_state_3)-min(observed_pr_data_state_3))));
Tranning_Predictand_state3=((Pr_tranning_3*(length(Pr_tranning_3)-1))+0.5)/length(Pr_tranning_3);

%Vector Space of observed data predictor(Temp) on the basis of rainfall
%state tranning period
Observed_data_predictor_Rainfall_state=[score1(:,1:Ln_var_explained) IDX];
Observed_predictor_data_state_1=(Observed_data_predictor_Rainfall_state(Observed_data_predictor_Rainfall_state(:,end)==1, 1:end-1));
Observed_predictor_data_state_2=(Observed_data_predictor_Rainfall_state(Observed_data_predictor_Rainfall_state(:,end)==2, 1:end-1));
Observed_predictor_data_state_3=(Observed_data_predictor_Rainfall_state(Observed_data_predictor_Rainfall_state(:,end)==3, 1:end-1));
%Vector Space of testing data(Predictor:Temp)on the basis of rainfall state
Testdata_predictor_Rainfall_state=[Testing_Predictor_Date Temp_val(:,1:Ln_var_explained) Rain_state_Prediction_Traning_Period];
Testdata_state_1= Testdata_predictor_Rainfall_state(Testdata_predictor_Rainfall_state(:,end)==1, 1:end-1);
Testdata_state_2= Testdata_predictor_Rainfall_state(1<Testdata_predictor_Rainfall_state(:,end) & Testdata_predictor_Rainfall_state(:,end)<=2, 1:end-1);
Testdata_state_3= Testdata_predictor_Rainfall_state(Testdata_predictor_Rainfall_state(:,end)>2, 1:end-1);

for i=1:10
 %Bulid regression for state I
mX1=[ones(length(Observed_predictor_data_state_1),1) Observed_predictor_data_state_1];
vy1=Tranning_Predictand_state1(:,i);
vP1=betareg_main(vy1,mX1);
%Bulid regression for state II
mX2=[ones(length(Observed_predictor_data_state_2),1) Observed_predictor_data_state_2];
vy2=Tranning_Predictand_state2(:,i);
vP2=betareg_main(vy2,mX2);

%Bulid regression for state III
mX3=[ones(length(Observed_predictor_data_state_3),1) Observed_predictor_data_state_3];
vy3=Tranning_Predictand_state3(:,i);
vP3=betareg_main(vy3,mX3);
% Calculate the precipitation for Testing period or Validation period
Predicted_Rain_State1=[ones(length(Testdata_state_1),1) Testdata_state_1(:,4:end)]*vP1(2:end);
Predicted_Rain_State2=[ones(length(Testdata_state_2),1) Testdata_state_2(:,4:end)]*vP2(2:end);
Predicted_Rain_State3=[ones(length(Testdata_state_3),1) Testdata_state_3(:,4:end)]*vP3(2:end);

Rain(:,i)=[Predicted_Rain_State1;Predicted_Rain_State2;Predicted_Rain_State3];
Rain(Rain<0)=0;
end
% Arrange the Date for Validation or Testing period
Date=[datenum(Testdata_state_1(:,1:3));datenum(Testdata_state_2(:,1:3));datenum(Testdata_state_3(:,1:3))];
%combine the data (simulated precipiation with date)
Predcited_Precipitation=[Date Rain];
%sort the data based date
Precipitation=sortrows(Predcited_Precipitation,1);
% Final bind of simulated precipitation data with time 
Simulated_Precipitation=[Testing_Predictor_Date Precipitation(:,2:end)];
end


% PROGRAM TO GENERATE MULTI-SITE PRECIPITATION DATA USING BETA REGRESSION
% SOHOM MANDAL
% CREATED ON: MARCH 05, 2017
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Run Beta Regression with GCM historical data predictors%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Run this file Beta regression
clc
clear
% Number of Replicates: User specific; Use a Positive interger
prompt = {'Starting Year e.g. 1984 (Historical):','Ending Year e.g. 2000 (Historical):','Starting Year e.g. 2040 (Future):', 'Ending Year e.g. 2050 (Future):'};
dlg_title = 'Input: Timeframe';
num_lines = 1;
defaultans = {'1976','2005','2045','2055'};
answer =(inputdlg(prompt,dlg_title,num_lines,defaultans));
Histstart_time = str2num(answer{1});
Histend_time=str2num(answer{2});
Futstart_time = str2num(answer{3});
Futend_time=str2num(answer{4});

Pr_Obs = uigetfile({'*.csv'},'Pick a Observed Historical Precipitation File');
fprintf(1,'Reading the data!!\n')
y=xlsread(Pr_Obs);
GCM_Hist = uigetfile({'*.csv'},'GCM Predictor Variables (Historical)');
fprintf(1,'Reading the data!!\n')
x=xlsread(GCM_Hist);
GCM_Fut = uigetfile({'*.csv'},'GCM Predictor Variables (Future)');
fprintf(1,'Reading the data!!\n')
z=xlsread(GCM_Fut);
disp('Code is running! Please wait');
expression = ('\_');
splitStr1=regexp(GCM_Hist,expression,'split');
splitStr=regexp(GCM_Fut,expression,'split');
tf = strcmp(splitStr1(3),splitStr(3));
if tf==1; % Compare files name; making sure same GCMs data are using
    y(y(:,2)==2 & y(:,3)==29,:)=[]; % Remove the leap year date
    y=y((Histstart_time<=y(:,1) & y(:,1)<=Histend_time), :); % Slicing the data set according to input dataframe
    x(x(:,2)==2 & x(:,3)==29,:)=[]; % Remove the leap year date
    x=x((Histstart_time<=x(:,1) & x(:,1)<=Histend_time), :); % Slicing the data set according to input dataframe
    z(z(:,2)==2 & z(:,3)==29,:)=[]; % Remove the leap year date
    z=z((Futstart_time<=z(:,1) & z(:,1)<=Futend_time), :); % Slicing the data set according to input dataframe
    Simulated_Precipitation=Beta_Regression(x,y,z); % Calling the beta regression and running files
    
   %## WRITE OUTPUT FILES
 filename=num2str(cell2mat(strcat('BR','_',splitStr(3),'_',splitStr(4),'_',splitStr(5),'_',splitStr(6))));
 col_header={'Year', 'Month', 'Day', 'ELK','ERC','GLD','HEB','JHT','QIN','QSM','SAM','SCA','WOL'};
 xlswrite(filename,Simulated_Precipitation,'Sheet1','A2');     %Write data
 xlswrite(filename,col_header,'Sheet1','A1');     %Write column header
h = msgbox('Downscaling Completed'); % message box for complete the work 
else
    fprintf(2,'Error: GCM files are not matching!!\n')
end

 


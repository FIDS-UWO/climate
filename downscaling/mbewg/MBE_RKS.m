function [synth,t3]  = MBE_RKS(a1,numrep,dummy1,dummy2,dummy3,dummy4)
% MEB Beta
% ROSHAN
% CREATED ON: JULY 21, 2013

% clear all
% clc
% close all
% 
% load APPLE.dat
% data = sum(APPLE,2);
% a = [[1:length(data)]' data];
%a =[1 2 3 4 5; 4 12 36 20 8]';
% rand('state',99)
dummy  =  dummy1;
dummyx =  dummy2;

a = [[1:length(a1)]' a1];
[y,i1] = sort(a);

aa = [i1(:,2) y(:,2)];

t2 =[a aa];


aa1 = (aa(1:end-1,2)+aa(2:end,2))/2;
aa2 = mean(abs(a(2:end,2)-a(1:end-1,2)));
int_mid_points = [aa(1,2)-aa2; aa1; aa(end,2)+aa2];

dmean = zeros(length(a),1);
for i = 1:length(a)
    if i==1, dmean(i,1) = 0.75* aa(i,2) + 0.25*aa(i+1,2);
    elseif i==length(a), dmean(i,1) = 0.25* aa(i-1,2) + 0.75*aa(i,2);
    else dmean(i,1) = 0.25* aa(i-1,2) + 0.5*aa(i,2)+0.25* aa(i+1,2);
    end
end
t3 =[t2 dmean];
% figure
% plot(int_mid_points,'o-')

interval = zeros(length(a),1);
density = zeros(length(a),1);
for i = 1:length(a)
    interval(i,1)= abs(int_mid_points(i+1,1)-int_mid_points(i,1));
    density(i,1) = 1/(abs(int_mid_points(i+1,1)-int_mid_points(i,1))*length(a));
end
interval_den = [interval density];

denp=[];
for i = 1:length(aa)
    denp =[denp; int_mid_points(i,1) density(i,1);int_mid_points(i+1,1) density(i,1)];
end
% figure
% plot(denp(:,1),denp(:,2))

cum_den = [0; cumsum(prod(interval_den,2))];
% figure

imp_points = [cum_den int_mid_points];

% numrep = 999;
synth = [];
for k=1:numrep
    uni_draw = sort(rand(length(a),1));
    %uni_draw = sort([0.12 0.83 0.53 0.59 0.11])';

    inp_data = zeros(length(a),1);
    for i = 1:length(a)
        check = 1;
        j=1;
        while j<=length(a)
            if uni_draw(i,1)>=cum_den(j,1) && uni_draw(i,1)<=cum_den(j+1,1)
                checkp = j;
                check =0;
            else
                check = 1;
            end
            if check == 0, break, end;
            j=j+1;
        end
        aa = int_mid_points(checkp,1);
        bb = int_mid_points(checkp+1,1);
        x1 = cum_den(checkp,1);
        x2 = cum_den(checkp+1,1);

        inp_data(i,1) = aa + ((uni_draw(i,1)-x1)*(bb-aa)/(x2-x1));
    end
    rep = zeros(length(a),1);
    for i=1:length(a)
        rep(i1(i,2),1)= inp_data(i,1);
    end
    synth = [synth rep];
end
    


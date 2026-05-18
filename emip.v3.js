// ==UserScript==
// @name         Qime Bot v2.1 - Pro Ultimate (Fixed Sending)
// @match        *://qime.bqp.vn/*
// @run-at       document-start
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // ==========================================
    // 1. CẤU HÌNH & DANH BẠ
    // ==========================================
    const TELE_TOKEN = '8602187491:AAHU7D5qA_r7C-sOgUZKKNKZ-H5xVrjn7pw';
    const TELE_CHAT_ID = '-5123741407';
    const MY_ID = "0356911600@reeng/desktop";

    // --- DÁN DANH SÁCH LIÊN HỆ V2 CỦA BẠN VÀO ĐÂY ---
      // --- DANH SÁCH LIÊN HỆ (Hãy dán danh sách của bạn vào đây) ---
    const contactList = [
    { "name": "0399036791", "phones": ["0399036791"] },
    { "name": "0356911600", "phones": ["0356911600"] },
    { "name": "86@A.Hiếu.PTM.L1", "phones": ["039 5698488"] },
    { "name": "NgôDuyc42", "phones": ["0857281863"] },
    { "name": "HvKTQS.Vb2.3//.hữu.Cường", "phones": ["+84983195529"] },
    { "name": "Chú_Thắng", "phones": ["098-347-1678"] },
    { "name": "AnhHảiCN", "phones": ["0974006921"] },
    { "name": "NgaA1", "phones": ["0375235069"] },
    { "name": "Cô Thanh", "phones": ["0912219221"] },
    { "name": "XeHYHN@Group", "phones": ["0838266868"] },
    { "name": "Hậu.Tư.đình.TCCNQP", "phones": ["0812084082"] },
    { "name": "Bạn@.Kỳ Anh", "phones": ["+84911053258"] },
    { "name": "86.a.Huy@QuânHuấn", "phones": ["069536512"] },
    { "name": "Hà", "phones": ["0358300169"] },
    { "name": "86.TTĐH.e.Đại.97@kíp3", "phones": ["0989543709"] },
    { "name": "Bạn@Huy.bạn.cò", "phones": ["038 4558869"] },
    { "name": "86.a.Triều@V10", "phones": ["0985693959"] },
    { "name": "BBF", "phones": ["+84329654993"] },
    { "name": "12A1.Lan.Anh", "phones": ["0339768068"] },
    { "name": "98.A.Tùng.cắtTóc", "phones": ["096 3656575"] },
    { "name": "Kyc1", "phones": ["033 2171371"] },
    { "name": "BTTM-T.ký.TT.Nghĩa-A.Dũng", "phones": ["098 9261974"] },
    { "name": "Quangc42", "phones": ["0342914144", "0833576246"] },
    { "name": "86.a.Trung.QBTS@n3", "phones": ["+84913322611", "097 8843283"] },
    { "name": "Hải Sản", "phones": ["+841676141676"] },
    { "name": "12A2.THĐ.Hải.17", "phones": ["0965410512"] },
    { "name": "T5.nhập.bảng", "phones": ["0973102054"] },
    { "name": "Tư.Đình.Căn.tin", "phones": ["0984653014"] },
    { "name": "Hoàn", "phones": ["0961013970", "0338558954"] },
    { "name": "A.Tuấn.Hv.PKQK", "phones": ["0817754728"] },
    { "name": "86.A.Vương@BTC", "phones": ["0868515960"] },
    { "name": "86A.Thái@P.SAFE", "phones": ["0869939025"] },
    { "name": "HiệpGàc42", "phones": ["0987081692"] },
    { "name": "86.TTĐH.A.Dũng.TTtr-tele", "phones": ["+84 39 7569 069"] },
    { "name": "Vb2.comrang.biahoi", "phones": ["0989675444"] },
    { "name": "Anh Tung (1)", "phones": ["098-798-0392"] },
    { "name": "Hiep", "phones": ["+84333746178"] },
    { "name": "Chị.Hiền@T.ChínhPTM", "phones": ["0975238782"] },
    { "name": "Co thuy", "phones": ["0975913729"] },
    { "name": "VillaHB", "phones": ["0377618626"] },
    { "name": "Anh Tung", "phones": ["0987980392"] },
    { "name": "22.thượng.đình.a.Tuấn.Anh", "phones": ["0983260390"] },
    { "name": "Thuy d", "phones": ["0362776873"] },
    { "name": "TrangNguyen", "phones": ["0372575839"] },
    { "name": "Quang Pk", "phones": ["0965340859"] },
    { "name": "thủy", "phones": ["0961160697"] },
    { "name": "Chú tùng Xe Máy", "phones": ["0983662268"] },
    { "name": "Dat Dupont", "phones": [] },
    { "name": "Minh xoăn Xoăn", "phones": ["0978063197", "0936282367"] },
    { "name": "86@A.Long.T.chính.cũ", "phones": ["098 9267910"] },
    { "name": "86.TTĐH.A.dũng.TTtr-mobile", "phones": ["0981005568"] },
    { "name": "86.TTĐH.X.Thái@G.sát", "phones": ["0353990862"] },
    { "name": "A.Hiếu.TưĐìnhT5", "phones": ["096 7954955"] },
    { "name": "86@Duẩn-L3", "phones": ["035 7575223"] },
    { "name": "Thùy Dung", "phones": ["016975508691"] },
    { "name": "86.A.Kiên@TLTH", "phones": ["0972993636"] },
    { "name": "86.V10.A.Tú", "phones": ["0916067155"] },
    { "name": "86@Chị.Thảo@B.T.Chính", "phones": ["0976763124"] },
    { "name": "C42 QuỳnhCẩu", "phones": ["0365663080", "0385933045"] },
    { "name": "86.a.Hải@4/CN", "phones": ["0974006921"] },
    { "name": "Anh Tuấn - Bác Sinh", "phones": ["0965641234"] },
    { "name": "Diep k", "phones": ["0394369454"] },
    { "name": "84.A.Linh@TCĐT", "phones": ["0989022992"] },
    { "name": "ÔngDương", "phones": ["0397838275"] },
    { "name": "86.Tt.P.Trung.TMT86", "phones": ["0869935566"] },
    { "name": "Co Kim", "phones": ["0973700470"] },
    { "name": "Khánh X2", "phones": ["0829988985", "0969005519"] },
    { "name": "Minh12A1", "phones": ["0978063197"] },
    { "name": "Em.Tùng.nhà.Dì.Huệ", "phones": ["097 1121365"] },
    { "name": "A Tuấn", "phones": ["01672103375"] },
    { "name": "PhanC42", "phones": ["0981231060"] },
    { "name": "Minh Cún", "phones": ["0971549455", "0833685111"] },
    { "name": "Đ Cường", "phones": ["+84373864281"] },
    { "name": "A tùng", "phones": ["097-226-0130", "0972260130"] },
    { "name": "Chú.Anh.sửa.điện.Thiện.Phiến", "phones": ["0986985428"] },
    { "name": "Trần.Linh-c2", "phones": ["0349326885"] },
    { "name": "Bus207", "phones": ["0988800755"] },
    { "name": "86.A.Hải@n3.2", "phones": ["0975869714"] },
    { "name": "Hvktqs.Bcb.Chị.Hải", "phones": ["0977117070"] },
    { "name": "86.TTĐH.Tuấn@n2", "phones": ["098 2156465"] },
    { "name": "Co Tkuy", "phones": ["01226334558"] },
    { "name": "Huyền Chiến", "phones": ["0983641829"] },
    { "name": "160KhâmThiên Trọ@Côchủ69Đạiđồng", "phones": ["0982240838"] },
    { "name": "Bộn Bề Bống", "phones": ["0398438949"] },
    { "name": "Thảo", "phones": ["0983139397"] },
    { "name": "Hoàng Sâm C2", "phones": ["0973238237"] },
    { "name": "86Anh2//Du", "phones": ["0962144828", "0978993478"] },
    { "name": "Co Lam~", "phones": ["00886917837120"] },
    { "name": "Co Hang. 10a1", "phones": ["0344029472"] },
    { "name": "Anh Hiếu 2", "phones": ["+841694190101"] },
    { "name": "86.P51.T5.Đỗ.Hưng.Hải.Phòng", "phones": ["0378348564"] },
    { "name": "CôHuongLy", "phones": ["0963143683"] },
    { "name": "86.TTĐH.a.Đàm.Đạt92", "phones": ["037 6578543"] },
    { "name": "A.cường.BTL.t.đô.BẮc.ninh", "phones": ["091 3912186"] },
    { "name": "Vb2.ĐTVT11.A.Việt", "phones": ["0348382065"] },
    { "name": "Chú Trọng", "phones": ["0983877536"] },
    { "name": "86.TTĐH.a.Hải93.1/CN", "phones": ["086 6882923"] },
    { "name": "Kyc3", "phones": ["038 4230995"] },
    { "name": "86.TrungKiên@VP", "phones": ["0987174879"] },
    { "name": "Hải Thanh", "phones": ["0393040711"] },
    { "name": "86.a.huy@PTM_Lữ2", "phones": ["0384421232"] },
    { "name": "Kyc5", "phones": ["091 4448488"] },
    { "name": "Phạm Đức Mạnh", "phones": ["+84 96 607 01 97"] },
    { "name": "Phương - Đã Bỏ A6", "phones": ["0966876160"] },
    { "name": "Duc A3", "phones": ["01627647498"] },
    { "name": "Cheń", "phones": ["0395776981"] },
    { "name": "86.A.Nguyễn.Thế.Anh.Rada.K57", "phones": ["096 6446483"] },
    { "name": "86.V10.A.Quyền", "phones": ["0983209142"] },
    { "name": "86.A.Lý@L3", "phones": ["098 4189492"] },
    { "name": "Wefinex.thầy.Lý.Hồng", "phones": ["033 3228482"] },
    { "name": "Buithihanghaigmailcom", "phones": ["+84983499699"] },
    { "name": "MinhA1", "phones": ["0978063197"] },
    { "name": "86.A.Long@BTC", "phones": ["0398344989", "0972999336"] },
    { "name": "Xe7.chỗ.Chú.Vượng", "phones": ["0987599039"] },
    { "name": "ChúCườngÔngDương", "phones": ["0912061884"] },
    { "name": "VinaMạng_3", "phones": ["091 9551820"] },
    { "name": "86.TTĐH.a.Sơn.Lu1", "phones": ["097 7448095"] },
    { "name": "Hoàng Long", "phones": ["+84 98 982 30 33", "+84989823033"] },
    { "name": "86.A.Cường@Cơ.yếu", "phones": ["0979689984"] },
    { "name": "Trang", "phones": ["01655151648"] },
    { "name": "Vb2.CTV.Hệ1.Chú.Thái", "phones": ["0383782368"] },
    { "name": "86.A.Hải@n3", "phones": ["0354950273"] },
    { "name": "XsKHA", "phones": ["0765922999"] },
    { "name": "KiênC42", "phones": ["0969180037"] },
    { "name": "Thắng", "phones": ["0346272012"] },
    { "name": "86.A.Nam@n2", "phones": ["0962910596"] },
    { "name": "86.Chị.Làn@BTChính", "phones": ["0979143612"] },
    { "name": "BácXuuân", "phones": ["0916076011"] },
    { "name": "86.TTĐH.A.Đức.Huy1/CN", "phones": ["0942858855"] },
    { "name": "DuyTL", "phones": ["0334533465"] },
    { "name": "Em.khánh....", "phones": ["0395886152"] },
    { "name": "Khải D", "phones": ["0375989399"] },
    { "name": "Vịt Thành Luân", "phones": ["0913211347"] },
    { "name": "Chức", "phones": ["039 4569233"] },
    { "name": "Ngoan A1", "phones": ["0705722468"] },
    { "name": "Thịnh", "phones": ["01634915259"] },
    { "name": "VũNgọcSơnC42", "phones": ["0338905860"] },
    { "name": "Dương Bch", "phones": ["0962822325"] },
    { "name": "Huệ", "phones": ["0333756193"] },
    { "name": "Bcb.hvktqs.A.Lăng", "phones": ["097 5113425"] },
    { "name": "86@Chú.Thái@PAT", "phones": ["+84989951053"] },
    { "name": "Nhà Trọ", "phones": ["086 8205612"] },
    { "name": "Ng Trang", "phones": ["0936792732"] },
    { "name": "Bảo Vệ Tư đình", "phones": ["0869515586"] },
    { "name": "Quyền@mẹ", "phones": ["098 6099316"] },
    { "name": "XeHY-HN", "phones": ["0389888091"] },
    { "name": "86.Chú.Dân@BCB", "phones": ["0985794119"] },
    { "name": "Vb2.Hệ1.Chị.Thắng", "phones": ["098 1191926"] },
    { "name": "Ngữ@a1", "phones": ["0971462472"] },
    { "name": "Em.Thịnh-nhàngoaibácthảo", "phones": ["0969248736"] },
    { "name": "86.A.Đức@TC", "phones": ["0988647986"] },
    { "name": "Dat k", "phones": ["0365918345"] },
    { "name": "Miền", "phones": ["0329751271"] },
    { "name": "ĐN-XeMáyHaiAn", "phones": ["093 5220490"] },
    { "name": "86AnhTúTC", "phones": ["0988737320"] },
    { "name": "Phượng", "phones": ["0373598248"] },
    { "name": "PKKQ.d4.A.Dũng@TrLCT", "phones": ["0335251221"] },
    { "name": "Cô Vân", "phones": ["0913798398"] },
    { "name": "Thành 12a1", "phones": ["0983846200"] },
    { "name": "ThànH", "phones": ["0348321093"] },
    { "name": "A.Minh@K1", "phones": ["0978270027"] },
    { "name": "huyên bun", "phones": ["0398865306"] },
    { "name": "86.a.Hoàn@K2000", "phones": ["0974033248", "0376713443"] },
    { "name": "Vb2.Chị.Duyên.Hệ1", "phones": ["097 9978308"] },
    { "name": "86.A.Kiên@n2", "phones": ["0981014858"] },
    { "name": "Trọ A Trường", "phones": ["098 3527302"] },
    { "name": "86.A.Bảo@n2", "phones": ["0981507792"] },
    { "name": "86.a.Du.TrbQBTS", "phones": ["0364537828"] },
    { "name": "03213887002", "phones": ["03213887002"] },
    { "name": "SửaNóngLạnh.TưĐình", "phones": ["0985764628"] },
    { "name": "Trọ Cô HÀ 10/3", "phones": ["036 5856947"] },
    { "name": "Bạn@Dũng_bạn.cò.chén", "phones": ["0374841059"] },
    { "name": "Yến Điê (1)", "phones": ["+84961107004"] },
    { "name": "Khai 10a1", "phones": ["096-655-4376", "0966554376"] },
    { "name": "Xuân.Quảng", "phones": ["0988117371"] },
    { "name": "BánhMìThịtNướng-tôn.thất.thiệp", "phones": ["0963169875"] },
    { "name": "Dương Nghé 💜", "phones": ["0357211198"] },
    { "name": "Pzakak", "phones": ["+84 8 3539 7790"] },
    { "name": "86.TTĐH.a.Phương@TrbQBTS", "phones": ["0989666800"] },
    { "name": "NamTom", "phones": ["0865178697"] },
    { "name": "86.TTĐH.e.Vịnh99.1/CN", "phones": ["0903203792"] },
    { "name": "Vy Bch", "phones": ["0974799468"] },
    { "name": "TheWay YouLie Love", "phones": ["35 6911600"] },
    { "name": "Vb2.A.Giang.CNTT11", "phones": ["036 8399966"] },
    { "name": "Anh Linh", "phones": ["0974208415"] },
    { "name": "Spyder@A.Hoài", "phones": ["0914333545"] },
    { "name": "86.a.Thi@BTC", "phones": ["0916948486"] },
    { "name": "86.A.Tiến@n1", "phones": ["036 3725089", "083 2370235"] },
    { "name": "Hiền", "phones": ["0328334069"] },
    { "name": "Oanh", "phones": ["+84978156423"] },
    { "name": "Sim@Sỹ.", "phones": ["0942121566"] },
    { "name": "ĐN-taxi", "phones": ["0935135844"] },
    { "name": "Viết", "phones": ["0359474486", "0966058806"] },
    { "name": "86@.a.Long.PTS.BTM", "phones": ["0966219182"] },
    { "name": "Vina_mạng2", "phones": ["0835283191"] },
    { "name": "Duy Tiên", "phones": ["01662368605"] },
    { "name": "86.A.Du@n3----", "phones": ["0962144828"] },
    { "name": "Hoàizoe", "phones": ["0392061698"] },
    { "name": "Co Tra`", "phones": ["0988032200"] },
    { "name": "86.chú.trung@BanQL", "phones": ["0912630688"] },
    { "name": "86.TTĐH.a.Thanh.Tùng94.2/", "phones": ["0364649426"] },
    { "name": "Bác Hùng", "phones": ["0942334921"] },
    { "name": "A.Hiếu@B.Long", "phones": ["086-921-1017"] },
    { "name": "AnhÂnK18", "phones": ["098-215-5037"] },
    { "name": "Vy Tùng", "phones": ["0364284049"] },
    { "name": "86.a.Quang.Bình.BTC", "phones": ["0978352552"] },
    { "name": "Kiên Tạ", "phones": ["0961125436"] },
    { "name": "TCĐT@A.Trường.k2", "phones": ["0333341638"] },
    { "name": "EmNhi", "phones": ["0858418898", "0944771906"] },
    { "name": "86Quý@n3", "phones": ["0868764578"] },
    { "name": "86@.a.Yến.CY", "phones": ["0339643286"] },
    { "name": "Kaito", "phones": ["+84 97 310 20 54"] },
    { "name": "A.Hoang.....", "phones": ["0385171750"] },
    { "name": "Hĩm.Trần-Thảo", "phones": ["0377823863"] },
    { "name": "Bố.Hòa", "phones": ["033 4327258"] },
    { "name": "Chú Hải (1)", "phones": ["0916171843"] },
    { "name": "86.a.DQ.Minh.Tú@Qh", "phones": ["0978626685"] },
    { "name": "Lan Anh_AnHy", "phones": ["+84365820319"] },
    { "name": "86.TTĐH.a.Thao", "phones": ["+84 97 661 66 11"] },
    { "name": "0164 490 5199", "phones": ["+84344905199"] },
    { "name": "86.TTĐH.D.Minh@n2", "phones": ["035 6087117", "0918456651"] },
    { "name": "Bác Xuâ", "phones": ["+84337163860"] },
    { "name": "C42.A.Tuyên.HvPkkq", "phones": ["0978687381"] },
    { "name": "Quyền", "phones": ["0988614197"] },
    { "name": "Bánh_mỳ_TranPhuSt", "phones": ["0763113626"] },
    { "name": "86.a.Bùi.Mạnh.Hà.17.2//PCT.BTH", "phones": ["097 3456848"] },
    { "name": "BQP.T.ký.BT.Chú.Quảng", "phones": ["0975479838"] },
    { "name": "T Quyên", "phones": ["0326348971", "0373564132"] },
    { "name": "86.a.Tuân@T5", "phones": ["0981515804"] },
    { "name": "86.A.Mạnh.QuânHuấn.pC.Trị", "phones": ["0989788190"] },
    { "name": "86.TTĐH.A.Tuấn.bQBTS", "phones": ["0976162150"] },
    { "name": "Kyc4", "phones": ["038 6499729"] },
    { "name": "1.4.Chị.thủy.9+11.40.chính.kinh", "phones": ["086 9353595"] },
    { "name": "86@c.Hằng.bTổChức.PCT", "phones": ["0973884015"] },
    { "name": "Vb2.1//ng.Vũ.Cường@ĐTVT11", "phones": ["0962110333"] },
    { "name": "@Tiến", "phones": ["070 2105502"] },
    { "name": "1.Ngõ113.cựLộc", "phones": ["094 6972998"] },
    { "name": "Vb2.A.Hải.Rượu.QK2", "phones": ["097 5231744"] },
    { "name": "86.A.Mạnh@n1", "phones": ["0962664432"] },
    { "name": "TiếnAnhT9", "phones": ["0333246169"] },
    { "name": "86.Yến@SMCC", "phones": ["0348885584"] },
    { "name": "Vb2.cntt11.A.Hiệp.pkkq", "phones": ["096 3337586"] },
    { "name": "86.A.Nghĩa", "phones": ["0868897555"] },
    { "name": "Xã.TưPháp.a.Dương", "phones": ["0987977439"] },
    { "name": "L anh", "phones": ["841673703318"] },
    { "name": "86.chị.hồng@n1", "phones": ["0356101995"] },
    { "name": "86A cuong@n2", "phones": ["0345223332"] },
    { "name": "86.aTuân@v10", "phones": ["0989391207"] },
    { "name": "AnhThÔng", "phones": ["0982895163"] },
    { "name": "86.a.CN.Trần.Quân.BHC", "phones": ["098 2184681"] },
    { "name": "HùngD7", "phones": ["0355188490"] },
    { "name": "Dương", "phones": ["01657039197", "+84395810324"] },
    { "name": "Anh Hanh (1)", "phones": ["0978298720"] },
    { "name": "86A H. Anh@n2", "phones": ["0932460250"] },
    { "name": "Đông", "phones": ["0392796960"] },
    { "name": "86.A.Vương@BQBTS", "phones": ["0975850285"] },
    { "name": "Hvktqs.Hùng.97.bộmônxe", "phones": ["0394316923"] },
    { "name": "1.2.s9/55/38chínhKinh", "phones": ["0965514493"] },
    { "name": "Dương-E.Phương.Thủy@2k", "phones": ["0985869741"] },
    { "name": "Phuong t", "phones": ["0328776987"] },
    { "name": "86.a.Hào.BTC", "phones": ["0989696000"] },
    { "name": "Vũ6", "phones": ["0987238237"] },
    { "name": "86.BTC.A.T.N.Sơn", "phones": ["0396978388"] },
    { "name": "86.a.trọng@n1", "phones": ["0383888378"] },
    { "name": "Quyên 4", "phones": ["0374659931"] },
    { "name": "Volibia", "phones": ["01656911600"] },
    { "name": "86.2/CN.DươngMinh@n2", "phones": ["0356087117"] },
    { "name": "PhúcC42", "phones": ["0971986284", "0375066900"] },
    { "name": "86.chú.TùngHưng.PTM", "phones": ["098 3043325"] },
    { "name": "Em.Đạt@b6.315", "phones": ["0968170998"] },
    { "name": "86.a.Trường@bQL", "phones": ["0966008600"] },
    { "name": "86.TTĐH.A.Dũng@n3", "phones": ["0355095509"] },
    { "name": "B Định", "phones": ["0366770562"] },
    { "name": "Tuyền", "phones": ["0962290924"] },
    { "name": "86@chị.Thư.Tài.chính", "phones": ["0985660595"] },
    { "name": "AThinh42", "phones": ["0978544068"] },
    { "name": "Phương@A6-Bỏ", "phones": ["0966876419"] },
    { "name": "Hnghĩa", "phones": ["0968986048"] },
    { "name": "86.Vina_mạng", "phones": ["0947724841"] },
    { "name": "Vina-mạng-SE", "phones": ["091 5553471"] },
    { "name": "Bà", "phones": ["035 8095635"] },
    { "name": "86.VT.Vui.vẻ", "phones": ["0983501116"] },
    { "name": "Wef.ThuThuỷ", "phones": ["+84 38 8160 605"] },
    { "name": "Kyc2", "phones": ["038 2649682"] },
    { "name": "1.1.79cựLộc.2p4tr", "phones": ["0988720498"] },
    { "name": "BQP@A.Ngọ@TCCNQP", "phones": ["0904905111"] },
    { "name": "86.A.Trường@HC", "phones": ["0969918095"] },
    { "name": "86.a.Sim@BCB", "phones": ["0973498059"] },
    { "name": "Hvktqs.125.1//CN.Nguyên", "phones": ["037 3113967"] },
    { "name": "Phong a2", "phones": ["0358315236"] },
    { "name": "86.TTĐH@CầuHNTT", "phones": ["553501"] },
    { "name": "Thag l", "phones": ["0383535885"] },
    { "name": "86.A.Giang@P_PTM", "phones": ["0986043522"] },
    { "name": "86.A.Huấn2//@B.CBộ.PC.Trị", "phones": ["0988398345"] },
    { "name": "86.TTĐH.A.Hẹ", "phones": ["096 8295021"] },
    { "name": "86.A.Ngọc@BTC", "phones": ["033 7285205"] },
    { "name": "TeleBinance", "phones": ["0918945636"] },
    { "name": "86.A.Bảo.Tuấn@BTC", "phones": ["+84356102188", "0902526989"] },
    { "name": "Thang B", "phones": ["0329654993"] },
    { "name": "86.A.Đức@Q.y", "phones": ["0397720011"] },
    { "name": "CaoRắn", "phones": ["036 2066714"] },
    { "name": "Chén", "phones": ["0388741898"] },
    { "name": "Thanhcapi | UG Ventures", "phones": ["+84 96 233 61 66"] },
    { "name": "Duy TL", "phones": ["0364122444"] },
    { "name": "Hvktqs.LTB.A.Đạo.qk38", "phones": ["096 8469060"] },
    { "name": "Định", "phones": ["0918785822"] },
    { "name": "Hĩm.Trần@Thảo", "phones": ["0333095455"] },
    { "name": "Huyen c", "phones": ["0382478070"] },
    { "name": "Nhân Bác", "phones": ["0375485847"] },
    { "name": "Vb2.cantin", "phones": ["0367234668"] },
    { "name": "Vutien", "phones": ["086 7907231"] },
    { "name": "BQP@E.Dũng@TCCNQP", "phones": ["0788621999"] },
    { "name": "BácHùng", "phones": ["0839425525"] },
    { "name": "Ngoan@a1", "phones": ["0962376610"] },
    { "name": "C42.Quê.Sơn", "phones": ["086 5630696"] },
    { "name": "Mơ", "phones": ["0369693816"] },
    { "name": "Sáng Cave", "phones": ["0367226730"] },
    { "name": "Hòa@A1", "phones": ["0967129306"] },
    { "name": "Wef.A.Hiếu.Tony.Trade", "phones": ["038 5396732"] },
    { "name": "Vinh Tạ", "phones": ["0336245356"] },
    { "name": "BácThảo", "phones": ["0948638555"] },
    { "name": "Phong Chó", "phones": ["0979799709"] },
    { "name": "Vb2.A.Toán.CNTT11", "phones": ["+84966191843"] },
    { "name": "86@A.Mạnh.thư.kí.TL", "phones": ["0976757911"] },
    { "name": "86.A.Chí@n1", "phones": ["0965599968"] },
    { "name": "86.A.Bảo.T5", "phones": ["0984616382"] },
    { "name": "ChịThảo", "phones": ["0968227812"] },
    { "name": "Platform@A.Quân", "phones": ["0338326383", "0917337383"] },
    { "name": "Lớp trưởng", "phones": ["0336036135"] },
    { "name": "Bánh_mì_34A", "phones": ["096-859-2658"] },
    { "name": "XeThaiBinhđiCaoToc", "phones": ["0968215868"] },
    { "name": "DươngTan", "phones": ["0357158654"] },
    { "name": "86.A.Thắng@BTC", "phones": ["033 2884728"] },
    { "name": "HvKTQS@vb2.Thầy.Hoàn.TRR", "phones": ["0374538022"] },
    { "name": "AnhBang", "phones": ["0986919561"] },
    { "name": "86.A.Đông@Lữ1", "phones": ["0983482238"] },
    { "name": "86.Chị.PhươngVănThư", "phones": ["0904426991", "0968100091"] },
    { "name": "86.TTĐH.a.Thành.Trung96.1/CN", "phones": ["096 6823043"] },
    { "name": "86.A.Việt@n3", "phones": ["0964376596"] },
    { "name": "0348583800", "phones": ["034-858-3800", "0348583800"] },
    { "name": "Dương A2", "phones": ["+84916358615"] },
    { "name": "Hvktqs.Q.y.Tt125", "phones": ["0974624541"] },
    { "name": "Bác Long", "phones": ["098 9346683"] },
    { "name": "Co Hang", "phones": ["0979929655"] },
    { "name": "c41ChungTú", "phones": ["0328854404"] },
    { "name": "AnhHiếu", "phones": ["0964048851"] },
    { "name": "86@A.Trinh@văn.thư", "phones": ["0962540239"] },
    { "name": "86.A.Cường@n2", "phones": ["0345223332"] },
    { "name": "86@.A.Tuyên.K2000", "phones": ["033 2051398"] },
    { "name": "86a.Q.Dũng@n2", "phones": ["0977519395"] },
    { "name": "86.A.Thiện.Thư.ký.TL@VP", "phones": ["0373666888"] },
    { "name": "C42.Nam.Tôm", "phones": ["0865178697"] },
    { "name": "Liễu Cute", "phones": ["0383601330"] },
    { "name": "Dat", "phones": ["0397043185"] },
    { "name": "Em", "phones": ["0334851812"] },
    { "name": "Bac Nguyet", "phones": ["0982852053"] },
    { "name": "86.TTĐH.A.vHuy93.3/", "phones": ["0326660423"] },
    { "name": "B6_315@Khang", "phones": ["096-293-0516"] },
    { "name": "Mai Văn Phiến", "phones": ["0923493905"] },
    { "name": "Toàn Di", "phones": ["0393036330"] },
    { "name": "Bác.Loan.-Trưởng.Đức", "phones": ["0377993315"] },
    { "name": "Sướng", "phones": ["0965829639"] },
    { "name": "Cô hường", "phones": ["037 5626679"] },
    { "name": "Vb2.ĐTVT.11.HvKTQS.Đặng.Minh.Tú.Sơn.Tây", "phones": ["+84973715279"] },
    { "name": "Bà Ngoại Dương", "phones": ["086 9157826"] },
    { "name": "Vb2.CNTT12.Ng.Quốc.Mạnh.Viện.Nhiệt.Đới.HN", "phones": ["0977230693"] },
    { "name": "Bác Nhân", "phones": ["0388206276"] },
    { "name": "86@E.TrungT6", "phones": ["037 7490903"] },
    { "name": "Bác sinh", "phones": ["0943969128"] },
    { "name": "Sửa Điện Thoại Ba Hàng", "phones": ["0986253259"] },
    { "name": "Cháo HIỀN Béo Vĩnh yên", "phones": ["093 6106198"] },
    { "name": "Ngoại-Vợ_Bà.Lựu", "phones": ["0344498121"] },
    { "name": "ChúChiến.Bố.E.Nhung", "phones": ["0367597396"] },
    { "name": "Vb2@Tường.98.HP.@Lu2.CNTT13", "phones": ["086 8370212"] },
    { "name": "Cậu Hiệu nhà Dương", "phones": ["0917819199"] },
    { "name": "86@A.Luật.P51.T5", "phones": ["039 4400377"] },
    { "name": "Anh.Ninh.Bạn.A.Q.Dũng.n2@86", "phones": ["+84965689231"] },
    { "name": "Vb2.A.Linh", "phones": ["0376941556"] },
    { "name": "Hvktqs@Cô.Hồng.V.CNTT", "phones": ["+84372576968"] },
    { "name": "Hvktqs@Cô.Hường.V.CNTT", "phones": ["+84973080942"] },
    { "name": "86@Phí.Cường.TrP.PM.v10", "phones": ["+84 98 9830870"] },
    { "name": "Hvktqs.1//.Vũ.Trọng.Kim@k9.kv125", "phones": ["0973632997"] },
    { "name": "Mẹ.Hà", "phones": ["036 5206202"] },
    { "name": "Chú cảnh Cạnh Bà Ngoại Dương", "phones": ["038 9487083"] },
    { "name": "Nguyen Thi Thuy Duong", "phones": ["0357211198"] },
    { "name": "Ông Nội Dương", "phones": ["0377274733"] },
    { "name": "Anh.Nam.Con.rể.bác.Quỳnh", "phones": ["0865818662"] },
    { "name": "Bác.Duân.nhà Duân", "phones": ["0375210603"] },
    { "name": "A.Tiến.sửa.xe.Ngã4.Hoàng.Ngân", "phones": ["+84972030696"] },
    { "name": "Tran Thi Hong Nhung", "phones": ["0398438949"] },
    { "name": "MBBank.NV", "phones": ["0936259327"] },
    { "name": "Vb2.A.Kiên.94.3/.Qk2-HvQY", "phones": ["035 2070894"] },
    { "name": "86.Anh.Hưng.96.Lu2.PTM", "phones": ["0967120696"] },
    { "name": "86.L2.Lộc.97.Hưng.Yên.Kim.Động.code.giỏi", "phones": ["0908139202"] },
    { "name": "86.Lu2.Hoàng.98.p.máy.chủ.Mien.Nam", "phones": ["0961805747"] },
    { "name": "Điện.lạnh.Phong.6", "phones": ["0906614714"] },
    { "name": "Hvktqs.H1.Chú.Hồng.Hệ.phó", "phones": ["+84912066869"] },
    { "name": "Hvktqs.125.Chú.Khiêm.QL.vệ.binh", "phones": ["0982423688"] },
    { "name": "Bác.Quỳnh", "phones": ["097 5570210"] },
    { "name": "Hvktqs.Viện.CNTT.Thầy.Khánh", "phones": ["0962393883"] },
    { "name": "Hvktqs.Thầy.Ngọc.CTĐ.CTCT.VY", "phones": ["+84983573526"] },
    { "name": "86@V10.Hưng.bếp", "phones": ["0566034444"] },
    { "name": "4Đ.A.phong.TCHC", "phones": ["0345326666"] },
    { "name": "Bác.Tuấn.Nội.nhà.Dương.Cương.Chính", "phones": ["0988454972"] },
    { "name": "Anh.Đạt.Nội.Dương.Cương.Chính", "phones": ["0365932162"] },
    { "name": "86.BCB.A.Thắng.2//", "phones": ["097 2091998"] },
    { "name": "HvKtQs.BM.CNPM.Thầy.Trung.Dũng.2//", "phones": ["+84 96 6035095"] },
    { "name": "HvPkkq@P.Đ.Tạo.Ng.Thành.Quân", "phones": ["0978910058"] },
    { "name": "HvPKKQ@Bộ.môn.Hóa.Lý.Cô.Nga3//", "phones": ["098 8677427"] },
    { "name": "HvPKKQ@P.ĐT.1//.Cù.Huy.Hùng", "phones": ["0981170085"] },
    { "name": "Cụ.của.Cún", "phones": ["0936671554"] },
    { "name": "Cây.Giống.HvNN.Tạ.Quyên", "phones": ["0839673666"] },
    { "name": "Xe.Việt.Hưng-ĐakNong", "phones": ["097 2389660"] },
    { "name": "Xe.Việt.Hưng-2", "phones": ["098 3114784", "097 4161912"] },
    { "name": "Shop.hoa.lụa.Phú.Lãm", "phones": ["036 5285003"] },
    { "name": "Vĩnh.Yên.Donker", "phones": ["0974469482"] },
    { "name": "Dương-Em.Phương.Anh", "phones": ["+84326793888"] },
    { "name": "Hậu@Anh.Doãn.Đức.Thế.biển.số.xe.HY", "phones": ["097 2559559"] },
    { "name": "Cô Lương", "phones": ["0385548793"] },
    { "name": "Vòng Hoa Cây Đa", "phones": ["0342566703"] },
    { "name": "Chú.Bình@PKKQ.PTL.TMT.QC-PKKQ@ChúSơn", "phones": ["+84983072425"] },
    { "name": "Đồng Nát Thiện Phiến", "phones": ["0862033135"] },
    { "name": "Họ-Ông.Thanh(Đua)", "phones": ["0911127691"] },
    { "name": "Bánh Mì Me Linh", "phones": ["096 9440800"] },
    { "name": "Kanvin Vux 🇳🇿 - netflix D", "phones": ["+84 97 232 98 68"] },
    { "name": "V10.A.Tuấn.(Thư.kí.CU.BTL)", "phones": ["086 8515980"] },
    { "name": "Chú.Bình.Cô.Thanh", "phones": ["098 2008668"] },
    { "name": "86@Chị.Trang.Tài.Chính@T5", "phones": ["098 2963269"] },
    { "name": "86.A.Sơn.QH.CQ.BTL", "phones": ["0966597424"] },
    { "name": "86@Chị.Hoa", "phones": ["0988424260"] },
    { "name": "86@Chị.Hạnh.Hậu.Cần.Doanh.Trại", "phones": ["098 2170772"] },
    { "name": "86@Trl.Hưng.PTC/CCT", "phones": ["086 8898597"] },
    { "name": "86@A.Long.BCT.BTM", "phones": ["097 9046768"] },
    { "name": "Dạy.Lái.Xe.Thầy.Vấn", "phones": ["0977635562", "0903205435"] },
    { "name": "PhươngMikita", "phones": ["039 6240733"] },
    { "name": "Bố", "phones": ["0794199932"] },
    { "name": "86@Chị.Thảo.PTC.BTL", "phones": ["0358008188"] },
    { "name": "86@C.Uyên.Bếp.CQ", "phones": ["098 3273039"] },
    { "name": "17.ngõ9.thuê.nhà.Anh.Phong", "phones": ["0936073372"] },
    { "name": "Head Honda Cổ Linh", "phones": ["0983392969"] },
    { "name": "86.A.Thanh.CNCT.T186", "phones": ["0966623868"] },
    { "name": "86@A.Quyền.PCT.T186", "phones": ["038 2293636"] },
    { "name": "86@Đức.Anh.TrL.Cụm12", "phones": ["0367800275"] },
    { "name": "86@A.Thủy.Đội7.cụm12", "phones": ["0967048238", "0326673218"] },
    { "name": "86@E.Mạnh.c7.1cm2.t186", "phones": ["039 8853284"] },
    { "name": "86@Dũng.c7.cm12", "phones": ["+84 88 885 60 00"] },
    { "name": "Vnvc", "phones": ["0389260595"] },
    { "name": "86@.Vũ.Khắc.Minh.v486", "phones": ["097 2171160"] },
    { "name": "86@.A.Hạnh.ct6.cm12.t186", "phones": ["038 3514255", "079 8494666"] },
    { "name": "86@A.Duy.93.c5.cm12.t186", "phones": ["037 9379898"] },
    { "name": "Changgg Nông", "phones": ["+84 329252317"] },
    { "name": "86@E.Duy.c6cm12.t186", "phones": ["+84 348535948"] },
    { "name": "86@Chị.Hoàng.Thị.Quỳnh.Mai.c6.cm12.t186", "phones": ["+84 39 3964 690", "039 3964690"] },
    { "name": "Đức Anh cmb12.t186 - Bỏ", "phones": ["+84 357691056"] },
    { "name": "86@A.Linh.cmt.cm12.t186", "phones": ["096 4475555"] },
    { "name": "86@A.Hiếu.Pcmt.cm12.t186", "phones": ["086 5294936"] },
    { "name": "86@A.Bằng.ct5.cm12.t186", "phones": ["096 2987736"] },
    { "name": "86@A.Hoàng.Anh.Pct5.cm12.t186", "phones": ["034 8303196"] },
    { "name": "86@.A.ĐT.Dũng.c5.cm12.t186", "phones": ["038 2265301"] },
    { "name": "86@Nông.Thị.Trang.c5.cm12.t186", "phones": ["032 9252317"] },
    { "name": "86@Lê.Học.Đại.c5.cm12.t186", "phones": ["091 2489903", "0328299069"] },
    { "name": "86@Vũ.Hoài.Nam.c5.cm12.t186", "phones": ["032 6528265"] },
    { "name": "86@Tô.Mạnh.Đạt.c5.cm12.t186", "phones": ["037 3888903"] },
    { "name": "86@Lê.Hồng.Sơn.c5.cm12.t186", "phones": ["033 2202255"] },
    { "name": "86@Đức.Minh.Duy.c6.cm12.t186", "phones": ["0348535948"] },
    { "name": "86@Mai.Hữu.Thế.c6.cm12.t186", "phones": ["038 8970901"] },
    { "name": "86@Nguyễn.Hữu.Hưng.Kiên.c6.cm12.t186", "phones": ["097 5899009"] },
    { "name": "86@Nguyễn.Thị.Hải.Yến.c7.cm12.t186", "phones": ["034 9531144"] },
    { "name": "86@Phạm.Văn.Duyên.c7.cm12.t186", "phones": ["097 1693560"] },
    { "name": "86@Nguyễn.Ngọc.Nhi.c7.cm12.t186", "phones": ["086 5120169"] },
    { "name": "86@Ngô.Minh.Lăng.c7.cm12.t186", "phones": ["036 8577250"] },
    { "name": "86@A.Đức.Thắng.PTC.BTM", "phones": ["0963795885"] },
    { "name": "86@A.Phong.TrL.TCTT.PTM.T186", "phones": ["038 9594808"] },
    { "name": "86@E.Đạt.cm13", "phones": ["035 9536816"] },
    { "name": "Just Do it!!!", "phones": ["+84 58 4587 058"] },
    { "name": "86@A.Hùng.PTM.T186", "phones": ["098 6614191"] },
    { "name": "86@1/CN.Ph.V.Nghiên.cm13.t186.97", "phones": ["096 9087304"] },
    { "name": "Thầy Vấn - Mạnh", "phones": ["0355888532"] },
    { "name": "Thầy Vấn-Thiện", "phones": ["0964740362"] },
    { "name": "Bác Hưng", "phones": ["0979383628"] },
    { "name": "86@A.Hoàn.Tr.Máy.chủ.PTM.t186", "phones": ["039 5849686"] },
    { "name": "86@A.Hoàng.pct.c6.cm12.t186", "phones": ["+84364771128"] },
    { "name": "86@e.Ng.Thanh.Long.c6cm12t186", "phones": ["096 5853998"] },
    { "name": "86@E.Dương.Trung.Hiếu.c6.cm12.t186", "phones": ["0867709860"] },
    { "name": "86@2/CN.Ng.Tiên.Phong.NvPCT", "phones": ["097 4252596"] },
    { "name": "Bác Quyên - Gas", "phones": ["098 7403932"] },
    { "name": "FPT.Hà.Nội.Hương.Giang", "phones": ["0329290006"] },
    { "name": "86@A.Huỳnh.CTV.cm12", "phones": ["+84973751762"] },
    { "name": "Ông Then", "phones": ["032 7581661"] },
    { "name": "86@e.Toàn.PCT.t186", "phones": ["0963790126"] },
    { "name": "Xe.tải.chuyển.nhà.Phố.Xốm", "phones": ["0389814765"] },
    { "name": "Vinh.FPT.Quê.HY", "phones": ["0963944442"] },
    { "name": "86@E.Bùi.Đức.Đại.c6cm12t186", "phones": ["+84 33 9293 033"] },
    { "name": "86@Ng.Mạnh.Đức.TL.PTM.T186", "phones": ["0392699990"] },
    { "name": "86@2/.Tr.Huy.Hoàng.c11.cm13.t186", "phones": ["0969867566"] },
    { "name": "Tiến - Đào huyền HY", "phones": ["097 1848665"] },
    { "name": "86@A.Đặng.Quốc.Phương.Béo.aTT.t186", "phones": ["0868813881"] },
    { "name": "Vòng Hoa Chợ Ba hàng", "phones": ["+84916900388"] },
    { "name": "86@A.Hà.Anh.P.HCKT.t186", "phones": ["0963839867"] },
    { "name": "Tuấn Đạt mobile PC.HY", "phones": ["098 6623989"] },
    { "name": "FPT.Hưng.Yên", "phones": ["0976828162"] },
    { "name": "Chị.Tươi.BH.Thai.sản", "phones": ["0911555186"] },
    { "name": "FPT.Thu.Uyên.HY", "phones": ["097 2315356"] },
    { "name": "@86.A.Hùng.Nv.Doanh.Trại.PHC.T186", "phones": ["097 2260992"] },
    { "name": "86@.E.Nguyễn.Huy.Nguyên.cm13.t186", "phones": ["+84 8 6670 1403", "+84866701403"] },
    { "name": "Bánh Mỳ Đa Tốn", "phones": ["035 2392562"] },
    { "name": "Xe TĐL - Yên Nghĩa", "phones": ["097 2571444", "+84968739618"] },
    { "name": "Quyết.Thắng.mobile", "phones": ["086 8236061"] },
    { "name": "86@Chú.Tuấn.HCKT.t186", "phones": ["0979188031"] },
    { "name": "86@Đoàn.Trần.Thái.Sơn.a.Xe.t186", "phones": ["096 2645901"] },
    { "name": "86@.chị.Nga.Quân.y.t186", "phones": ["+84 98 4028941"] },
    { "name": "86@.A.Ngô.Kim.Cương.PCHT.T186", "phones": ["0988190666"] },
    { "name": "86@E.Phí.Minh.Phương.c5.cm12.t186", "phones": ["094 6601222"] },
    { "name": "86@E.Bảo.c6.cm12", "phones": ["+84 91 612 75 66"] },
    { "name": "86@Em.Bảo.c6.cm12.t186", "phones": ["0916127566"] },
    { "name": "Cô Hoa.cho Thuê Nhà Đa Tốn.61 ngõ 95", "phones": ["0988263486"] },
    { "name": "Cô Phú - Nhà Trọ 2tr", "phones": ["0964607425"] },
    { "name": "ChủTrọ.A.Thành.Đa.Tốn", "phones": ["0987419217"] },
    { "name": "Phương.ny.Bống", "phones": ["0987210167"] },
    { "name": "Cơm.Đa.Tốn", "phones": ["098 5373005"] },
    { "name": "86@3/.A.Mạnh.HC-KT.T186", "phones": ["035 2003815"] },
    { "name": "86@E.Giang.Văn.Linh.cm13.t186", "phones": ["0962674906"] },
    { "name": "Cục.Tuyên.Huấn.TCTT.A.Vương.(86 cũ)", "phones": ["0866627366"] },
    { "name": "A.Tùng.Bác.Sinh", "phones": ["0962246111"] },
    { "name": "86.V4.1//.A.Chung.CNCT", "phones": ["0983154613"] },
    { "name": "86@chị.Nghị.PCT.t186", "phones": ["0869344868"] },
    { "name": "V.KHQS.V.CNTT.a.Ng.Sinh.Huy.Kiem.Phieu", "phones": ["098 2726964"] },
    { "name": "Shiper.shopee.Trình", "phones": ["0981277991"] },
    { "name": "86@A.Mạnh.Trl.CT.CCT.BTL", "phones": ["036 9529894"] },
    { "name": "86@Chị.Hoàn.Quân.nhu.CHCKT", "phones": ["0976457242"] },
    { "name": "86@A.Hội.CN-HCKT.T5", "phones": ["098 2338902"] },
    { "name": "Chị.Nhã.yakout", "phones": ["032 9519259"] },
    { "name": "MIO-Thảo.Kendy", "phones": ["098 2863666"] },
    { "name": "Máy.Lọc.Nước.Đa.Tốn.An.Canh", "phones": ["0979869683"] },
    { "name": "Khăn.Bông.THái.Bình", "phones": ["039 6907573"] },
    { "name": "Xuân.Bắc.TCĐT.k3", "phones": ["0868684720"] },
    { "name": "Em.Hai.e.trai.Khánh", "phones": ["0327785094"] },
    { "name": "Vận Tải Minh Anh Thái Nguyên", "phones": ["092 8285285"] },
    { "name": "Xe.Ghép_HY-HN_xe.điện", "phones": ["0979592655"] },
    { "name": "Xiaome Hiếu", "phones": ["+84 89 812 42 59"] },
    { "name": "Xe Minh Anh Ship Hàng Thái Nguyên", "phones": ["0364661298"] },
    { "name": "86@Nam_Bếp.186", "phones": ["078 3138025"] },
    { "name": "Chị.Thủy_thuốc.Bình.Vị.Nam", "phones": ["0973069062"] },
    { "name": "86@Nguyễn.Hồng.Quân.97.pHCKT.T186.", "phones": ["0976494349"] },
    { "name": "Máy.Thêu.A.Hòa.Giám.Đốc.HN", "phones": ["091 2115986"] },
    { "name": "86@Từ.Quang.Minh.c12.cm13.t186", "phones": ["0962955047"] },
    { "name": "Quê.Hưng.gạch.Tét.nước", "phones": ["0983743689"] },
    { "name": "86@Ng.Vũ.Hoàng.Long.c5cm12.t186", "phones": ["0366100901"] },
    { "name": "Khánh.Tam.Đảo.Khách.Sạn.Thi.Lái.xe", "phones": ["094 1020992"] },
    { "name": "A.Đức.Chị.Thảo", "phones": ["0915020904"] },
    { "name": "86@Quách.Phương.Nam.97.cm13", "phones": ["0973058751"] },
    { "name": "86@A.Bui.Thanh.Cao.4/.Trạm.Máy.Chu.PTM.T186", "phones": ["0989113882"] },
    { "name": "86@A.Lộc.Tr.Máy.chủ.PTM.t186", "phones": ["0334403443"] },
    { "name": "86@a.Hậu.at.VB.t186", "phones": ["0382351556"] },
    { "name": "86@.Đinh.Sơn.Hải.PTM.T186", "phones": ["0374358590"] },
    { "name": "Khánh.X@Hà", "phones": ["085 6220399"] },
    { "name": "86@A.Nguyễn.Thế.Sơn.PTM.T186", "phones": ["098 3923268"] },
    { "name": "Cơm Đa Tốn 40k", "phones": ["094 8102096"] },
    { "name": "86@A.Chinh.p.TĐHCH.V486", "phones": ["098 6856415"] },
    { "name": "86.Đỗ.Duy.Mạnh.p.TĐHCH.V486", "phones": ["096 8886602"] },
    { "name": "Bác.Nguyệt-A.Chung", "phones": ["0919853959"] },
    { "name": "Bác.Nguyệt@A.Chung-A.Kiên", "phones": ["097 9266226"] },
    { "name": "C.an.Xã.Bát.Tràng.a.Đức", "phones": ["076 6119199"] },
    { "name": "Duy DM", "phones": ["+84 55 9375 904"] },
    { "name": "Chị.Thảo.DQTV.@A.Nam", "phones": ["0368190985"] },
    { "name": "Bác.Nguyệt@A.Linh", "phones": ["0917676766"] },
    { "name": "Anh Hiếu cmt12 - 2", "phones": ["+84 97 816 65 98"] },
    { "name": "Uni.sửa.chuột", "phones": ["0966816866"] },
    { "name": "kháng xuân xuân kháng", "phones": ["+84 97 518 76 48"] },
    { "name": "86@E.Kháng.2k3.c6.cm12.t186", "phones": ["0975187648"] },
    { "name": "Hà Phương", "phones": ["+84 98 420 77 42"] },
    { "name": "Cơm.Công.Bình.Gia.Lâm", "phones": ["098 6203376"] },
    { "name": "86@A.Khánh.cm13", "phones": ["0988147325"] },
    { "name": "Phuong Trang", "phones": ["+84 8 4669 6888"] },
    { "name": "86@A.Thuận.PCT.T186", "phones": ["0975123876"] },
    { "name": "86@E.P.Trang.cm12.t186", "phones": ["084 6696888"] },
    { "name": "86@.Vũ.Ngọc.Sơn.97.c6.cm12.t186", "phones": ["0932261938"] },
    { "name": "86@a.Thế.Sơn.PTM.T186", "phones": ["0973804492"] },
    { "name": "86@A.Cao.Đức.Duy.Tr.May.Chủ.T186", "phones": ["0962560562"] },
    { "name": "Cô.Xuyến.vợ.chú.Tuấn.ông.Trung", "phones": ["033 9147339"] },
    { "name": "86@A.Tùng.bếp.t186", "phones": ["0868414999"] },
    { "name": "86@A.Tuấn.Ngọc.cm11", "phones": ["0983898083"] },
    { "name": "86@Khiêm.Cấn.c6.cm12", "phones": ["0385573595"] },
    { "name": "86@A.Lâm.cmt.cm13.t186", "phones": ["0972108210"] },
    { "name": "86@A.Hiếu.HCKT.t186", "phones": ["0961995395"] },
    { "name": "86@A.Minh.bếp.t186", "phones": ["037 4627603"] },
    { "name": "Dì Huệ", "phones": ["0965758327"] },
    { "name": "Chú.Thoan", "phones": ["0974816939"] },
    { "name": "86@An.c6cm12", "phones": ["0326668825"] },
    { "name": "Quê@E.Hà.Hồng", "phones": ["0986207231"] },
    { "name": "0823109791 86@E.Nhi.c6.cm12", "phones": ["0823109791"] },
    { "name": "86@A.Phạm.Huỳnh.Đức.PTC.BTM", "phones": ["035 7844452"] },
    { "name": "86@a.Hùng.ct.c6", "phones": ["0335867701"] },
    { "name": "86@A.Huân.Cơ.Yếu.T186", "phones": ["0984291888"] },
    { "name": "Chú.Chinh@con.ông.Hiếu", "phones": ["0972546907"] },
    { "name": "86@.a.Hùng.ct.c6.cm12.t186", "phones": ["0989523476"] },
    { "name": "Bán Hàng Trưng Bày", "phones": ["0936551355"] },
    { "name": "0326513241 86@e.Toàn.c5.cm12.t186", "phones": ["0326513241"] },
    { "name": "Dịch.vụ.công.xã.Tiên.Lữ", "phones": ["0983875532"] },
    { "name": "86@3//CN.Nguyễn.Hồng.Anh.NV.P.ATTT.BTL", "phones": ["098 2727051"] },
    { "name": "86@E.Dũng.cm13.t186", "phones": ["037 5300930"] },
    { "name": "86.TTĐH.BTL.TS", "phones": ["538577", "538523"] },
    { "name": "86@E.Mai.Tiến.Hùng.c6cm12t186", "phones": ["0834009386"] },
    { "name": "Tư.Đình@A.Lăng", "phones": ["0388083943"] },
    { "name": "86@E.Sùng.Thị.út.c6.cm12.t186", "phones": ["0336266267"] },
    { "name": "86@E.Mai.Tiến.Hùng.c6cm12.t186", "phones": ["0866986803"] },
    { "name": "86@A.Nguyễn.Đức.Việt.c7.cm12.t186", "phones": ["0928866833"] },
    { "name": "86@Em.Nguyễn.Trung.Kiên.c6cm12t186", "phones": ["0988437312"] },
    { "name": "Cơm Rang Thảo Nguyên", "phones": ["036 9643606"] },
    { "name": "86@A.Trương.Tùng.BTC.T186", "phones": ["0983730373"] },
    { "name": "Đài.VTV@Chị.Yến.Sản.xuất", "phones": ["0989919398"] },
    { "name": "ĐÀI.VTV@a.Tài.95.Họa.sĩ.dàn.cảnh", "phones": ["0966648095"] },
    { "name": "Đài.VTV@A.Công.Sản.xuất.83", "phones": ["087 8556655", "0369831441"] },
    { "name": "Anh.Việt.Đào.tết", "phones": ["097 6559431"] },
    { "name": "Em.Xuân.nhà.chú.Dũng", "phones": ["097 4640655"] },
    { "name": "86@A.Công.PTM.t186-96", "phones": ["0966585996"] },
    { "name": "86@Mạnh.Trl.Cụm11", "phones": ["0376144269"] },
    { "name": "86@E.Ngọc.Nguyên.Cm13", "phones": ["0376932183"] },
    { "name": "86@.Em.Phú.c6cm12", "phones": ["0968869964"] },
    { "name": "86@E.Hiếu.c7cm12t186", "phones": ["+84866489699"] },
    { "name": "86@A.Khánh.Tài.chính.t186", "phones": ["0889977997"] },
    { "name": "0862247128 86@E.Ngọc.Phương.C7.cm12.t186", "phones": ["0862247128"] },
    { "name": "Local.Bác.Quý", "phones": ["089 6789145"] },
    { "name": "Local.Bác.Ngọc", "phones": ["089 9899851"] },
    { "name": "86@BCĐ.35.Thái.Nguyên.Chị.Lan", "phones": ["098 3851120"] },
    { "name": "Vườn Cây Giáp Hải", "phones": ["034 9409088"] },

     // Thêm nhóm vào đây:
    { "name": "Team6", "phones": ["0383514255_1748127945140"] },
    { "name": "NhomX", "phones": ["0356911600_1777970815034"] },
    { "name": "NhomDKRA_Cum", "phones": ["0367800275_1748423562198"] },
];

    let lastSocket = null;
    let lastUpdateId = 0;
    let isFetching = false;
    let processedIds = [];
    const MAX_CACHE = 1000;

    // ==========================================
    // 2. HÀM TIỆN ÍCH
    // ==========================================
    function toPascalCaseNoAccents(str) {
        if (!str) return "GroupUnknown";
        return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D')
            .replace(/[^a-zA-Z0-9 ]/g, '').split(' ').filter(word => word.length > 0)
            .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join('');
    }

    function normalizePhone(phone) {
        if (!phone) return "";
        let p = phone.toString().replace(/\D/g, '');
        if (p.startsWith('84')) p = '0' + p.substring(2);
        return p;
    }

    function getNameFromId(rawId) {
        if (!rawId) return "AnDanh";
        const cleanId = rawId.split('@')[0];
        const phoneId = normalizePhone(cleanId);
        const found = contactList.find(c => c.phones.some(p => normalizePhone(p) === phoneId) || c.phones.some(p => p === cleanId));
        return found ? found.name : cleanId;
    }

    function escapeHTML(str) {
        if (!str) return "";
        return str.replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
    }

    // ==========================================
    // 3. PHÂN TÍCH TIN NHẮN ĐẾN
    // ==========================================
    function analyzePacket(data) {
        if (typeof data !== 'string') return;
        if (data.includes("<message") && /subtype=['"]text['"]/.test(data) && data.includes('<body>')) {
            const idMatch = data.match(/id=['"]([^'"]+)['"]/);
            const msgId = idMatch ? idMatch[1] : null;
            if (msgId && processedIds.includes(msgId)) return;

            const bodyMatch = data.match(/<body>([\s\S]*?)<\/body>/);
            let body = bodyMatch ? bodyMatch[1] : "";
            if (!body.trim() || (body.length > 50 && !body.includes(' '))) return;

            const isGC = data.includes("type='groupchat'") || data.includes('type="groupchat"');
            const roomMatch = data.match(/room=['"]([^'"]+)['"]/);
            const fromMatch = data.match(/from=['"]([^@'"]+)@?/);
            const sourceRaw = fromMatch ? fromMatch[1] : "";
            const memberMatch = data.match(/member=['"]([^@'"]+)@?/);
            let senderRaw = isGC ? (memberMatch ? memberMatch[1] : sourceRaw) : sourceRaw;

            if (senderRaw.includes(MY_ID.split('@')[0])) return;

            let nameGrField = "", idGrField = "", sourceCopyable = "";
            if (isGC) {
                let groupRawId = sourceRaw;
                let originalRoomName = roomMatch ? roomMatch[1] : groupRawId;
                let foundGroup = contactList.find(c => c.phones.includes(groupRawId));
                let pascalName = foundGroup ? foundGroup.name : toPascalCaseNoAccents(originalRoomName);
                if (!foundGroup) contactList.push({ "name": pascalName, "phones": [groupRawId] });
                sourceCopyable = `Nhóm: <code>${escapeHTML(originalRoomName)}</code>`;
                nameGrField = `📁 <b>NameGr:</b> <code>${pascalName}</code>\n`;
                idGrField = `🆔 <b>idGr:</b> <code>${groupRawId}</code>\n`;
            } else { sourceCopyable = `<code>Cá nhân</code>`; }

            const senderDisplayName = getNameFromId(senderRaw);
            if (msgId) { processedIds.push(msgId); if (processedIds.length > MAX_CACHE) processedIds.shift(); }

            const text = `<b>📩 TIN NHẮN MỚI</b>\n👤 <b>Từ:</b> <code>${escapeHTML(senderDisplayName)}</code>\n🏢 <b>Nguồn:</b> ${sourceCopyable}\n${nameGrField}${idGrField}💬 <b>Nội dung:</b>\n<tg-spoiler>${escapeHTML(body)}</tg-spoiler>\n\n⏰ <i>Lúc: ${new Date().toLocaleTimeString()}</i>`;
            sendTele(text);
        }
    }

    // ==========================================
    // 4. LỆNH TELEGRAM & GỬI TIN ĐI
    // ==========================================
    async function sendTele(text) {
        try {
            await fetch(`https://api.telegram.org/bot${TELE_TOKEN}/sendMessage`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chat_id: TELE_CHAT_ID, text: text, parse_mode: 'HTML' })
            });
        } catch (e) {}
    }

    function sendToQime(targetName, message) {
        if (!lastSocket || lastSocket.readyState !== 1) {
            return { success: false, error: "WebSocket Offline. Hãy F5 lại trang Qime!" };
        }
        const found = contactList.find(c => c.name.toLowerCase() === targetName.toLowerCase() || c.phones.includes(targetName));
        const realTarget = found ? found.phones[0].replace(/\s+/g, '') : targetName;
        const isGroup = realTarget.includes('_');
        const targetId = realTarget.includes('@') ? realTarget : (realTarget + (isGroup ? "@muc.reeng" : "@reeng"));
        const msgId = "050" + (isGroup ? "2" : "1") + "000_" + Math.random().toString(36).substr(2, 9).toUpperCase();
        let xml = isGroup
            ? `<message f_opr="04" from="${MY_ID}" id="${msgId}" subtype="text" to="${targetId}" type="groupchat"><cstate>1</cstate><body>${message}</body></message>`
            : `<message f_opr="04" from="${MY_ID}" id="${msgId}" subtype="text" t_opr="04" to="${targetId}" type="chat"><body>${message}</body></message>`;
        try { lastSocket.send(xml); return { success: true, target: found ? found.name : realTarget }; }
        catch (e) { return { success: false, error: e.message }; }
    }

    async function checkTeleCommands() {
        if (isFetching) return;
        isFetching = true;
        try {
            const res = await fetch(`https://api.telegram.org/bot${TELE_TOKEN}/getUpdates?offset=${lastUpdateId + 1}&timeout=10`);
            const data = await res.json();
            if (data.ok && data.result.length > 0) {
                for (const update of data.result) {
                    lastUpdateId = update.update_id;
                    const msg = update.message;
                    if (!msg || msg.chat.id.toString() !== TELE_CHAT_ID || !msg.text) continue;

                    // 1. Lệnh danh bạ
                    if (msg.text === "/danhbanhom") {
                        const groups = contactList.filter(c => c.phones.some(p => p.includes('_')));
                        let txt = "<b>📂 DANH BẠ NHÓM</b>\n\n";
                        groups.forEach(g => { txt += `👥 NameGr: <code>${g.name}</code>\n🆔 ID: <code>${g.phones[0]}</code>\n\n`; });
                        sendTele(txt);
                        continue;
                    }

                    // 2. Lệnh gửi tin nhắn: /mess [Tên] :: [Nội dung] ::
                    if (msg.text.startsWith("/mess")) {
                        // Regex mới: linh hoạt dấu cách, nhận diện chính xác cặp :: ::
                        const messMatch = msg.text.match(/^\/mess\s+(.+?)\s*::\s*([\s\S]+?)\s*::/);

                        if (messMatch) {
                            const target = messMatch[1].trim();
                            const content = messMatch[2].trim();
                            const result = sendToQime(target, content);
                            if (result.success) sendTele(`✅ Đã gửi tới <b>${escapeHTML(result.target)}</b>`);
                            else sendTele(`❌ Lỗi gửi: <code>${escapeHTML(result.error)}</code>`);
                        } else {
                            sendTele("⚠️ <b>Sai cú pháp!</b>\nHãy dùng: <code>/mess Tên :: Nội dung ::</code>");
                        }
                    }
                }
            }
        } catch (e) {} finally { isFetching = false; }
    }

    // ==========================================
    // 5. KHỞI TẠO & HOOK
    // ==========================================
    const _WS = window.WebSocket;
    window.WebSocket = function(url, protocols) {
        const socket = new _WS(url, protocols);
        lastSocket = socket;
        socket.addEventListener('message', (e) => analyzePacket(e.data));
        return socket;
    };

    setInterval(checkTeleCommands, 3000);

    window.addEventListener('load', () => {
        const div = document.createElement('div');
        div.style = "position:fixed;bottom:10px;right:10px;z-index:9999;background:rgba(0,0,0,0.8);color:#0f0;padding:8px;font-size:11px;border-radius:8px;border:1px solid #333;";
        div.innerText = "Qime Bot v2.1 Active";
        document.body.appendChild(div);
    });

})();
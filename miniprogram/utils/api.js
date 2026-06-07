// utils/api.js - API请求工具
const app = getApp()

function request(url, data = {}) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: app.globalData.apiBase + url,
      data: data,
      method: 'GET',
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(res.data)
        } else {
          reject('请求失败: ' + res.statusCode)
        }
      },
      fail: (err) => {
        reject('网络错误: ' + err.errMsg)
      }
    })
  })
}

module.exports = { request }
